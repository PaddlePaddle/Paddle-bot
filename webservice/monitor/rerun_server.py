import aiohttp
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
import sys
import os
import json
import requests
import logging
#sys.path.append("..")
from utils.auth import get_jwt, get_installation, get_installation_access_token
from utils.readConfig import ReadConfig
from utils.auth_ipipe import Sign, Get_ipipe_auth

routes = web.RouteTableDef()
router = routing.Router(routing.Router())

localConfig = ReadConfig(path='conf/config.ini')
logging.basicConfig(level=logging.INFO, filename='logs/auto_reun.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

here = Path(__file__).resolve().parent


def rerunCI(ciName, target_url):
    """
    1. get trigger id
    2. rerun
    """
    pipelineBuildid = target_url.split('/')[-3]
    stage_url = localConfig.cf.get('ipipeConf', 'stage_url') + pipelineBuildid
    session, req = Get_ipipe_auth(stage_url)
    res = session.send(req).json()
    triggerId = res['triggerId']

    session = requests.Session()
    rerun_url = 'https://xly.bce.baidu.com/open-api/ipipe/agile/pipeline/doRebuild?pipeTriggerId=%s' %triggerId
    req = requests.Request("GET", rerun_url, headers= {"Content-Type": "application/json", "IPIPE-UID": "Paddle-bot"}).prepare()
    query_param = 'pipeTriggerId=%s' %triggerId
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    try:
        res = session.send(req).status_code
    except Exception as e:
            print("Error: %s" % e)
            print('%s_%s rerun failed: %s' %(ciName, target_url, e))
            logger.error('%s_%s rerun failed: %s' %(ciName, target_url, e))
    else:
        print('%s_%s rerun success!' %(ciName, target_url))
        logger.error('%s_%s rerun success!' %(ciName, target_url))
    
async def getCIList(user, repo, PR, commit, gh):
    """
    1. get commit's CI list
    2. rerun all CI one by one
    """
    status_url = 'https://api.github.com/repos/%s/%s/statuses/%s' %(user, repo, commit)
    (code, header, body) = await gh._request("GET", status_url, {'Content-Type': 'application/json'})
    res = json.loads(body.decode('utf8'))
    REQUIRED_CI =  localConfig.cf.get('%s/%s' %(user, repo), 'REQUIRED_CI')
    commit_ci_status = []
    for ci in res:
        already_exit = False
        if ci['context'] != 'license/cla':
            for i in commit_ci_status:
                if ci['context'] == i['ciName'] and i['time'] > ci['created_at']: #删除一些脏数据 github api
                    already_exit = True
                    break
            if already_exit == False and ci['context'] in REQUIRED_CI:
                item_dic = {}
                item_dic['time'] = ci['created_at']
                item_dic['ciName'] = ci['context']
                item_dic['status'] = ci['state']
                item_dic['target_url'] = ci['target_url']
                rerunCI(ci['context'], ci['target_url'])
                commit_ci_status.append(item_dic)
    print('%s %s have been reruned!' %(PR, commit))
    logger.info('%s %s have been reruned!' %(PR, commit))

@routes.get('/{user}/{repo}/{PR}/{commit}')
async def main(request):
    """
    get http_server
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
                gh, jwt=jwt, installation_id=installation["id"]
            )
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(session, user,
                        oauth_token=access_token["token"])
            await getCIList(user, repo, PR, commit, gh)
        
        return web.Response(status=200, content_type='text/html', text="您好，正在帮您一键rerun所有的CI，请稍等...")

if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = 8081
    if port is not None:
        port = int(port)
    web.run_app(app, port=port)

