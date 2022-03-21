import os
import aiohttp
from gidgethub.aiohttp import GitHubAPI
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from utils.auth import get_jwt, get_installation, get_installation_access_token
import event
import json

routes = web.RouteTableDef()
router = routing.Router(event.router)


@routes.post("/")
@routes.post("/icafetogithub/label")
async def main(request):
    body = await request.read()
    if 'pr' in json.loads(body.decode('utf8')):
        PR = json.loads(body.decode('utf8'))['pr']
        label = json.loads(body.decode('utf8'))['label']
        repo = json.loads(body.decode('utf8'))['repo']
        user = repo.split('/')[0]
        isLabel = True
    else:
        user = json.loads(body.decode('utf8'))['repository']['owner']['login']
        repo = json.loads(body.decode('utf8'))['repository']['full_name']
        secret = os.environ.get("GH_SECRET")
        event = sansio.Event.from_http(request.headers, body, secret=secret)
        isLabel = False
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
            if isLabel == True:
                if label == 'testing':
                    label_github = ['status: testing']
                elif label == 'finished':
                    label_github = ['status: finished']
                label_url = 'https://api.github.com/repos/%s/issues/%s/labels' % (
                    repo, PR)
                await gh.post(label_url, data={"labels": label_github})
            else:
                await router.dispatch(event, gh, repo)

    return web.Response(status=200)


routes.get("/")


async def main(request):
    return web.Response(
        status=200, text="You have successfully installed the Paddle-bot app.")


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)
    web.run_app(app, port=port)
