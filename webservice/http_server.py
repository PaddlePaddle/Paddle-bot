from pathlib import Path
import os
import json
import logging
import aiohttp
from aiohttp import web
import aiohttp_jinja2
import jinja2
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from utils.readConfig import ReadConfig
from utils.test_auth_ipipe import xlyOpenApiRequest
from utils.auth import get_jwt, get_installation, get_installation_access_token

here = Path(__file__).resolve().parent

localConfig = ReadConfig('conf/config.ini')
logging.basicConfig(
    level=logging.INFO,
    filename='logs/auto_reun.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class rerunServer():
    def __init__(self):
        self.__rerunUrl = 'https://xly.bce.baidu.com/open-api/ipipe/agile/pipeline/doRebuild?pipeTriggerId='

    def rerunCI(self, ciName, target_url):
        """
        1. get trigger id
        2. rerun
        """
        pipelineBuildid = target_url.split('/')[-3]
        stage_url = localConfig.cf.get('ipipeConf',
                                       'stage_url') + pipelineBuildid
        res = xlyOpenApiRequest().get_method(stage_url).json()
        triggerId = res['triggerId']
        rerun_url = self.__rerunUrl + str(triggerId)
        query_param = 'pipeTriggerId=%s' % triggerId
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        res_status_code = xlyOpenApiRequest().get_method(
            rerun_url, param=query_param, headers=headers).status_code
        if res_status_code == 200:
            print('%s_%s rerun success!' % (ciName, target_url))
            logger.error('%s_%s rerun success!' % (ciName, target_url))
        else:
            print('%s_%s rerun failed: %s' %
                  (ciName, target_url, res_status_code))
            logger.error('%s_%s rerun failed: %s' %
                         (ciName, target_url, res_status_code))

    async def getCIList(self, user, repo, PR, commit, gh):
        """
        1. get commit's CI list
        2. rerun all CI one by one
        """
        status_url = 'https://api.github.com/repos/%s/%s/statuses/%s' % (
            user, repo, commit)
        (code, header, body) = await gh._request(
            "GET", status_url, {'Content-Type': 'application/json'})
        res = json.loads(body.decode('utf8'))
        REQUIRED_CI = localConfig.cf.get('%s/%s' % (user, repo), 'REQUIRED_CI')
        commit_ci_status = []
        for ci in res:
            already_exit = False
            if ci['context'] != 'license/cla':
                for i in commit_ci_status:
                    if ci['context'] == i['ciName'] and i['time'] > ci[
                            'created_at']:  #删除一些脏数据 github api
                        already_exit = True
                        break
                if already_exit == False and ci['context'] in REQUIRED_CI:
                    item_dic = {}
                    item_dic['time'] = ci['created_at']
                    item_dic['ciName'] = ci['context']
                    item_dic['status'] = ci['state']
                    item_dic['target_url'] = ci['target_url']
                    self.rerunCI(ci['context'], ci['target_url'])
                    commit_ci_status.append(item_dic)
        print('%s %s have been reruned!' % (PR, commit))
        logger.info('%s %s have been reruned!' % (PR, commit))

    @aiohttp_jinja2.template('reruning.html')
    async def rerun_handler(self, request):
        """
        rerun get server
        """
        user = request.match_info['user']
        repo = request.match_info['repo']
        PR = request.match_info['PR']
        commit = request.match_info['commit']
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
                    gh, jwt=jwt, installation_id=installation["id"])
                # treat access_token as if a personal access token
                gh = gh_aiohttp.GitHubAPI(
                    session, user, oauth_token=access_token["token"])
                await self.getCIList(user, repo, PR, commit, gh)


class failutsServer():
    def getFailedUT(self):
        """
        获取失败单测列表
        """
        with open("buildLog/lastestfaileduts.json", 'r') as load_f:
            try:
                lastestfaileduts = json.load(load_f)
            except json.decoder.JSONDecodeError:
                lastestfaileduts = {}
        load_f.close()
        if len(lastestfaileduts) == 0:
            data = {'faileduts': []}
        else:
            failed_uts_list = []
            for ut in lastestfaileduts:
                single_failed_ut = {}
                failed_ut = ut.split('(')[0].strip()
                failed_ut_ci_list = []
                for task in lastestfaileduts[ut]:
                    ci = task.split('_')[2]
                    failed_ut_ci_list.append(ci)
                failed_ut_ci_list = list(set(failed_ut_ci_list))
                single_failed_ut[failed_ut] = failed_ut_ci_list
                failed_uts_list.append(single_failed_ut)
            data = {'faileduts': failed_uts_list}
        return data

    async def failut_handler(self, request):
        """
        提供失败单测的get server
        """
        data = self.getFailedUT()
        return web.json_response(data)


if __name__ == "__main__":
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(here)))
    app.router.add_get('/{user}/{repo}/{PR}/{commit}',
                       rerunServer().rerun_handler)
    app.router.add_get('/faileduts', failutsServer().failut_handler)
    web.run_app(app, port=8081)
