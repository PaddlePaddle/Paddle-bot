import os
import aiohttp
import asyncio
import json
import datetime
import logging
import gidgethub
from gidgethub import aiohttp as gh_aiohttp
from utils.auth import get_jwt, get_installation, get_installation_access_token
from utils.mail_163 import Mail

logging.basicConfig(level=logging.INFO, filename='./logs/regularClose.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sendCloseMail(content, repo, receivers, CloseDay):
    mail = Mail()
    mail.set_sender('paddlepaddle_bot@163.com')
    mail.set_receivers(receivers)
    mail.set_title('%s repo关闭超过%s天未更新的issue/pr通知' %(repo, CloseDay))
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()

def getNextUrl(link):
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

async def overdueList(types, url, gh, CloseDay):
    today = datetime.date.today()
    lastYear = str(today - datetime.timedelta(days=CloseDay))
    logger.info("Close %s before %s" %(types, lastYear))
    overduelist = []
    while (url != None):
        print(url)
        (code, header, body) = await gh._request("GET", url, {'accept': 'application/vnd.github.antiope-preview+json', 'authorization': "token 25c171f52d4fa9cbe5704c95ee2fc5dad9528862"})
        res = json.loads(body.decode('utf8'))
        for item in res:
            if types == 'issues' and 'pull_request' not in item:
                if item['updated_at'] < lastYear: #if updateTime earlier than lastYear
                    user = item['user']['login']
                    comments_url = item['comments_url']
                    (code_co, header_co, body_co) = await gh._request("GET", comments_url, {'accept': 'application/vnd.github.antiope-preview+json', 'authorization': "token 25c171f52d4fa9cbe5704c95ee2fc5dad9528862"})
                    comments = json.loads(body_co.decode('utf8'))
                    if len(comments) != 0:
                        last_comment_user = comments[len(comments)-1]['user']['login']
                        if last_comment_user != user:
                            overduelist.append(item['number'])
            elif types == 'pr':
                if item['updated_at'] < lastYear: #if updateTime earlier than lastYear
                    overduelist.append(item['number'])
        url = getNextUrl(header['link'])
        #print(url)
        #url = None
    return overduelist

async def close(types, itemList, gh, user, repo):
    if types == 'pr':
        event = 'pulls'
    else:
        event = 'issues'
    data = {"state": "closed"}
    d = json.dumps(data)
    task_info = ""
    logger.info("close %s count is %s: %s" % (types, len(itemList), itemList))
    if len(itemList) != 0:
        for i in itemList:
            url = "https://api.github.com/repos/%s/%s/%s/%s" % (user, repo, event, i)
            try:
                await gh.patch(url, data=data)
                task_info = task_info + "<tr align=center><td>{}</td><td>{}</td></tr>".format(
                    types, i)
                logger.info("%s_id: %s closed success!" % (types, i))
            except gidgethub.BadRequest:
                logger.error("%s_id: %s closed failed!"  % (types, i))
    else:
        logger.info("%s is empty!" %itemList)
    return task_info

async def main(user, repo, repoMessage):
    async with aiohttp.ClientSession() as session:
        app_id = os.getenv("GH_APP_ID")
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
            pr_info = ''
            issue_info = ''
            for CloseType in repoMessage['CloseType']:
                if CloseType == 'issues':
                    issues_url = 'https://api.github.com/repos/%s/%s/issues?per_page=100&page=1&direction=asc&q=addClass' %(user, repo)
                    issueList = await overdueList('issues', issues_url, gh, repoMessage['CloseDay'])
                    logger.info('issueList: %s' %issueList)
                    issue_info = await close('issue', issueList, gh, user, repo)
                elif CloseType == 'pr':
                    pr_url = 'https://api.github.com/repos/%s/%s/pulls?per_page=100&page=1&direction=asc&q=addClass' %(user, repo)
                    PRList = await overdueList('pr', pr_url, gh, repoMessage['CloseDay'])
                    logger.info('PRList: %s' %PRList)
                    pr_info = await close('pr', PRList, gh, user, repo)
            if pr_info or issue_info:
                mail_content = "<html><body><p>Hi, ALL:</p> <p>以下issue/pr超过%s天未更新，将关闭</p> <table border='1' align=center> <caption><font size='3'></font></caption>" %repoMessage['CloseDay']
                mail_content = mail_content + "<tr align=center><td bgcolor='#d0d0d0'>类型</td><td bgcolor='#d0d0d0'>issue/pr号</td></tr>"
                task_info = pr_info + issue_info
                mail_content = mail_content + task_info + "</table></body></html>"
                sendCloseMail(mail_content, repo, repoMessage['receivers'], repoMessage['CloseDay'])
                logger.info("Mail sent success! ")
            else:
                logger.info("PR/issue without timeout")
            

def regularClose_job():
    regularClose_repo_dict = {'PaddleOCR': {'CloseDay': 90, 'receivers': ['zhangchunle@baidu.com', 'lichenxia@baidu.com'], 'CloseType': ['issues']}, 'Paddle': {'CloseDay': 365, 'receivers': ['zhangchunle@baidu.com', 'v_duchun@baidu.com', 'likunlun@baidu.com', 'chenshuo07@baidu.com'], 'CloseType': ['issues', 'pr']}}
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = asyncio.get_event_loop()
    for repo in regularClose_repo_dict:
        loop.run_until_complete(main('PaddlePaddle', repo, regularClose_repo_dict[repo]))