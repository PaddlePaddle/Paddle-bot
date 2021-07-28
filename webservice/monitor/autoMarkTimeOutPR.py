import os
import aiohttp
import asyncio
import json
import time
import datetime
import logging
import gidgethub
import requests
from gidgethub import aiohttp as gh_aiohttp
import sys
import pandas as pd
sys.path.append("..")
from utils.auth import get_jwt, get_installation, get_installation_access_token
from utils.test_auth_ipipe import xlyOpenApiRequest
from utils.readConfig import ReadConfig

logging.basicConfig(level=logging.INFO, filename='../logs/regularMark.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

localConfig = ReadConfig(path='../conf/config.ini')

class MarkTimeoutCI(object): 
    def __init__(self, user, repo, gh):
        self.pr_url = 'https://api.github.com/repos/%s/%s/pulls?per_page=100&page=1&q=addClass' %(user, repo)
        self.gh = gh
        self.user = user
        self.repo = repo
        self.mark_url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/job-builds/{}/mark'
        self.rerun_url = 'http://www.cipaddlepaddle.cn:8081/%s/%s/{}/{}' %(user, repo)
        self.comment_url = 'https://api.github.com/repos/%s/%s/issues/{}/comments' %(user, repo)

    def getNextUrl(self, link):
        """遍历所有的PR"""
        next_str = None
        for i in link.split(','):
            if 'rel="next"' in i:
                next_str = i
                break
        if next_str != None:
            start_index = next_str.index('<')
            end_index = next_str.index('>')
            url = next_str[start_index+1:end_index]
        else:
            url = None
        return url

    async def getBeforeSevenDaysPRList(self):
        """
        1. 获取距离现在7天-30天创建的PR列表:只获取，不做处理
        2. 30天之前的暂不处理: 默认认为GitHub已经设它们为code conflicts. 如有需要，后续在处理。
        return : [{PR, commit, status_url}]
        """
        today = datetime.date.today()
        seven_Days_ago = str(today - datetime.timedelta(days=7))
        month_Days_ago = str(today - datetime.timedelta(days=30))
        overduelist = [] 
        while (self.pr_url != None):
            print(self.pr_url)
            (code, header, body) = await self.gh._request("GET", self.pr_url, {'accept': 'application/vnd.github.antiope-preview+json'})
            res = json.loads(body.decode('utf8'))
            for item in res:
                if item['created_at'] < seven_Days_ago and item['created_at'] > month_Days_ago:
                    item_dic = {}
                    item_dic['PR'] = item['number']
                    item_dic['commit'] = item['head']['sha']
                    item_dic['status_url'] = item['statuses_url']
                    overduelist.append(item_dic)
            self.pr_url = self.getNextUrl(header['link'])
        print("before %s's PRs: %s" %(seven_Days_ago, overduelist))
        logger.info("before %s's PRs: %s" %(seven_Days_ago, overduelist))
        return overduelist

    async def getCIstatus(self):
        """
        获取符合条件的PR的CI列表:
        1. 获取PR最新的commit url
        2. 获取1的commit的最近的CI（去除一些GitHub的脏数据（eg. pending状态的））
        3. 判断最近的CI是否是7天之前的，只要有一条CI是7天之前的就需要标记
        4. 只标记成功的CI为失败
        """
        PRList = await self.getBeforeSevenDaysPRList()
        print(len(PRList))
        today = datetime.date.today()
        seven_Days_ago = str(today - datetime.timedelta(days=7))
        print(seven_Days_ago)
        CI_STATUS_LIST = []
        for item in PRList:
            print(item['PR'])
            commit_ci_status = {}
            commit_ci_status['PR'] = item['PR']
            commit_ci_status['commit'] = item['commit']
            status_url = item['status_url']
            res = requests.get(status_url, headers = {'authorization': "token ad4d5dea7caabf1137e6c3624183c7a64bf79c27"}, timeout=15).json()
            commit_ci_status['CI'] = []
            if_before_seven_day = [] #标记是否所有的CI都是7天之前的
            for ci in res:
                already_exit = False
                if ci['context'] != 'license/cla':
                    for i in commit_ci_status['CI']:
                        if ci['context'] == i['ciName'] and i['time'] > ci['created_at']: #删除一些脏数据 github api
                            already_exit = True
                            break
                    if already_exit == False:
                        item_dic = {}
                        item_dic['time'] = ci['created_at']
                        item_dic['ciName'] = ci['context']
                        item_dic['status'] = ci['state']
                        item_dic['markId'] = ci['target_url'].split('/')[-1]
                        commit_ci_status['CI'].append(item_dic)
                        if item_dic['time'] > seven_Days_ago: #最新的一次CI不是7天之前的
                            if_before_seven_day.append(False)
                        else:
                            if_before_seven_day.append(True) #True 是7天之前的
            if True in if_before_seven_day: #只要有一个CI是七天之前的就必须标记
                print('%s is 7 ago..........' %item['PR'])
                CI_STATUS_LIST.append(commit_ci_status)
            else:
                print('%s not 7 ago' %item['PR'])
        print("need to mark ci list: %s" %CI_STATUS_LIST)
        logger.info("need to mark ci list: %s" %CI_STATUS_LIST)
        return CI_STATUS_LIST

    async def markCIFailed(self):
        """
        mark success/pending ci to failed
        """
        CIStatusList = await self.getCIstatus()
        print("CIStatusList length: %s" %len(CIStatusList))
        REQUIRED_CI =  localConfig.cf.get('%s/%s' %(self.user, self.repo), 'REQUIRED_CI')
        DATA = {"data":"FAIL", "message":"Paddle-bot", "type": "MARK"}
        json_str = json.dumps(DATA)
        headers = {"Content-Type": "application/json", "IPIPE-UID": "Paddle-bot"}
        for item in CIStatusList:
            PR =  item['PR']
            commit = item['commit']
            ci_list = item['CI']
            mark_ci_list = []
            for ci in ci_list:
                if ci['ciName'] in REQUIRED_CI and ci['status'] in ['success', 'pending']:
                    print(ci['ciName'])
                    markId = ci['markId'] 
                    mark_url = self.mark_url.format(markId) 
                    res = xlyOpenApiRequest().post_method(mark_url, json_str, headers=headers)
                    print(res)
                    if res.status_code  == 200 or res.status_code  == 201:
                        mark_ci_list.append(ci['ciName'])
                        print('%s_%s_%s mark success!' %(PR, commit, ci['ciName']))
                        logger.info('%s_%s_%s mark success!' %(PR, commit, ci['ciName']))
                    else:
                        print('%s_%s_%s mark failed!' %(PR, commit, ci['ciName']))
                        logger.error('%s_%s_%s mark failed!' %(PR, commit, ci['ciName']))
            if len(mark_ci_list) > 0:
                marked = self.queryIfHasMark(PR, commit)
                if marked == False:
                    await self.inform(item)
                else:
                    print('%s_%s has marked!!!!' %(PR, commit))
                    logger.info('%s_%s has marked!!!!' %(PR, commit))
                data = {'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()), 'PR': PR,  'COMMITID': commit, 'CINAME': mark_ci_list}
                self.save_markci_job(data)
        
    def queryIfHasMark(self, PR, commitid):
        """marked 是否已经标记过"""
        marked = True
        df = pd.read_csv('../buildLog/mark_timeout_ci.csv')
        queryKey = df[(df['PR']==PR) & (df['COMMITID']==commitid)]
        if queryKey.empty:
            marked =  False
        print("has marked: %s" %marked)
        return marked

    def create_markci_csv(self, filename):
        """创建存储文件"""
        df = pd.DataFrame(columns=['TIME', 'PR', 'COMMITID', 'CINAME'])
        df.to_csv(filename)
        
    def save_markci_job(self, data):
        """将kill的任务存到"""
        filename = '../buildLog/mark_timeout_ci.csv'
        if os.path.exists(filename) == False :
            self.create_markci_csv(filename)
        write_data = pd.DataFrame(data)
        write_data.to_csv(filename, mode='a', header=False)

    async def inform(self, item):
        """Paddle-bot发出评论"""
        #POST /repos/:owner/:repo/issues/:issue_number/comments
        rerun_ci_link = self.rerun_url.format(item['PR'], item['commit'])
        comment_url = self.comment_url.format(item['PR'])
        shortId = item['commit'][0:7]
        #message = "Sorry to inform you that %s's CIs have passed for more than 7 days. To prevent PR conflicts, you need to re-run all CIs. You can re-run it manually, or you can click [`here`](%s) to re-run automatically." %(shortId, rerun_ci_link)
        message = "Sorry to inform you that %s's CIs have passed for more than 7 days. To prevent PR conflicts, you need to re-run all CIs manually. " %shortId
        print('%s inform!!!' %item['PR'])
        await self.gh.post(comment_url, data={"body": message})   

async def main(user, repo):
    async with aiohttp.ClientSession() as session:
        #app_id = os.getenv("GH_APP_ID")
        app_id = 59502
        jwt = get_jwt(app_id)
        gh = gh_aiohttp.GitHubAPI(session, user)
        try:
            installation = await get_installation(gh, jwt, user)
        except ValueError as ve:
            print(ve)
        else:
            access_token = await get_installation_access_token(
                gh, jwt=jwt, installation_id=installation["id"]
            )
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(session, user,
                        oauth_token=access_token["token"])
            markCIObject = MarkTimeoutCI(user, repo, gh)
            await markCIObject.markCIFailed()

loop = asyncio.get_event_loop()
loop.run_until_complete(main('PaddlePaddle', 'Paddle'))
