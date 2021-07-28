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

async def main(user):
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
            issues_url = 'https://api.github.com/repos/PaddlePaddle/Paddle/issues/32819/assignees'
            data = {"assignees": ['yaoxuefeng6']}
            print(await gh.post(issues_url, data=data))


loop = asyncio.get_event_loop()
loop.run_until_complete(main('PaddlePaddle'))
