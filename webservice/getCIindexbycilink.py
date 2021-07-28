import os
import aiohttp
import asyncio
import json
import datetime
import logging
import gidgethub
from gidgethub import aiohttp as gh_aiohttp
from utils.auth import get_jwt, get_installation, get_installation_access_token

logging.basicConfig(level=logging.INFO, filename='./logs/regularClose.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

async def getCIList(url, gh):
    ci_list = []
    while (url != None):
        (code, header, body) = await gh._request("GET", url, {'accept': 'application/vnd.github.v3+json'})
        res = json.loads(body.decode('utf8'))
        for item in res:
            sha = item['sha']
            print(sha)
            ci_list.append(sha)
        url = getNextUrl(header['link'])
    return ci_list

async def getcistatus(url, gh):

    (code, header, body) = await gh._request("GET", url, {'accept': 'application/vnd.github.v3+json'})
    res = json.loads(body.decode('utf8'))
    print(res)

async def main(user, repo):
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
            #commit_url = 'https://api.github.com/repos/%s/%s/commits?since=2020-12-20T16:00:00Z&until=since=2020-12-27T16:00:00Z&per_page=100&page=1&direction=asc&q=addClass' %(user, repo)
            #CIList = await getCIList(commit_url, gh)
            CIList = ['2e5b4a216cc7eb95f0968faeb2882439511b1aa7', '0c23ba95d8a98681da0faf0bf851c97e18ca4191', '7b2dc4e6b18f2c7d44f3c2eac079856c9660a692']
            for commit in CIList:
                status_url = 'https://api.github.com/repos/PaddlePaddle/Paddle/commits/%s/statuses' %commit
                await getcistatus(status_url, gh)


loop = asyncio.get_event_loop()
loop.run_until_complete(main('PaddlePaddle', 'Paddle'))
