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
async def main(request):
    body = await request.read()
    user = json.loads(body.decode('utf8'))['repository']['owner']['login']
    repo = json.loads(body.decode('utf8'))['repository']['full_name']
    secret = os.environ.get("GH_SECRET")
    event = sansio.Event.from_http(request.headers, body, secret=secret)
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
            await router.dispatch(event, gh, repo)
    return web.Response(status=200)

if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)
    web.run_app(app, port=port)
