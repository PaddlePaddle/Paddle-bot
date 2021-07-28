import os
import aiohttp
from gidgethub.aiohttp import GitHubAPI
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from utils.auth import get_jwt, get_installation, get_installation_access_token
import event
import json
import traceback

routes = web.RouteTableDef()
router = routing.Router(event.router)

def printException( e ):
    print('--------str(Exception):\t', str(Exception))
    print('str(e):\t\t', str(e))
    print('repr(e):\t', repr(e))
    print('Get information about the exception that is currently being handled')
    print('traceback.print_exc(): ', traceback.print_exc())
    exc_type, exc_value, exc_traceback = sys.exc_info() 
    print('e.message:\t', exc_value)
    print("Note, object e and exc of Class %s is %s the same." % 
              (type(exc_value), ('not', '')[exc_value is e]))
    print('traceback.format_exc():\n%s' % traceback.format_exc())
  

@routes.post("/")
async def main(request):
    body = await request.read()
    user = json.loads(body.decode('utf8'))['repository']['owner']['login']
    repo = json.loads(body.decode('utf8'))['repository']['full_name']
    secret='a23f5133b147e2bd6333f77f08d9f29f1d4f9e6e'
    try:
        event = sansio.Event.from_http(request.headers, body, secret=secret)
    except Exception as e:
        print('here')
        printException( e )
    else:
        async with aiohttp.ClientSession() as session:
            #app_id = os.getenv("GH_APP_ID")
            # TODO: use os.getenv("GH_APP_ID")
            app_id = '68547'
            jwt = get_jwt(app_id)
            gh = gh_aiohttp.GitHubAPI(session, user)
            try:
                installation = await get_installation(gh, jwt, user)
            except ValueError as ve:
                printException( ve )
            else:
                try:
                    access_token = await get_installation_access_token(
                        gh, jwt=jwt, installation_id=installation["id"]
                    )
                    # treat access_token as if a personal access token
                    gh = gh_aiohttp.GitHubAPI(session, user,
                                oauth_token=access_token["token"])
                    await router.dispatch(event, gh, repo)
                except Exception as e:
                    printException( e )
    return web.Response(status=200)

@routes.get("/")
async def main(request):
    return web.Response(status=200, text="You have successfully installed the Paddle-bot app.")

 
if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = os.environ.get("PORT")
    port = 8888 
    if port is not None:
        port = int(port)
    web.run_app(app, host='127.0.0.1', port=port)
