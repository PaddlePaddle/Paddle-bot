import os
import time
import jwt
import aiohttp
import traceback
from gidgethub import aiohttp as gh_aiohttp

def get_jwt(app_id):
    # TODO: read is as an environment variable
    #path_to_private_key = os.getenv("PEM_FILE_PATH")
    path_to_private_key = "just-test-paddle.2021-07-22.private-key.pem"
    pem_file = open(path_to_private_key, "rt").read()
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),
        "iss": app_id
    }
    try:
        encoded = jwt.encode(payload, pem_file, algorithm="RS256")
        # decode string as utf-8
        bearer_token = encoded.encode("utf-8").decode("utf-8")
    except Exception as e:
        print('aaaaaa:str(Exception):\t', str(Exception))
        print('str(e):\t\t', str(e))
        print('repr(e):\t', repr(e))
        print('Get information about the exception that is currently being handled')
        exc_type, exc_value, exc_traceback = sys.exc_info() 
        print('----------')
        print('e.message:\t', exc_value)
        print("Note, object e and exc of Class %s is %s the same." % 
                  (type(exc_value), ('not', '')[exc_value is e]))
        print('traceback.print_exc(): ', traceback.print_exc())
        print('traceback.format_exc():\n%s' % traceback.format_exc())
    else:
        print("No error")
    return bearer_token 

async def get_installation(gh, jwt, username):
    try:
        async for installation in gh.getiter(
            "/app/installations",
            jwt=jwt,
            accept="application/vnd.github.machine-man-preview+json",
        ):
            if installation["account"]["login"] == username:
                print('get login name: ', username)
                return installation
    except Exception as e:
        print("get_installation_exception:")
        traceback.print_exc()
        print('str(Exception):\t', str(Exception))
        print('str(e):\t\t', str(e))
        print('repr(e):\t', repr(e))
        # Get information about the exception that is currently being handled  
        exc_type, exc_value, exc_traceback = sys.exc_info() 
        print('e.message:\t', exc_value)
        print("Note, object e and exc of Class %s is %s the same." % 
                  (type(exc_value), ('not', '')[exc_value is e]))
        print('traceback.print_exc(): ', traceback.print_exc())
        print('traceback.format_exc():\n%s' % traceback.format_exc())
    raise ValueError(f"Can't find installation by that user: {username}")

async def get_installation_access_token(gh, jwt, installation_id):
    # doc: https: // developer.github.com/v3/apps/#create-a-new-installation-token
    access_token_url = (
        f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    )
    response = await gh.post(
        access_token_url,
        data=b"",
        jwt=jwt,
        accept="application/vnd.github.machine-man-preview+json",
    )
    return response

async def Github_APP_Auth():
    async with aiohttp.ClientSession() as session:
        #app_id = os.getenv("GH_APP_ID")
        app_id = 59502
        jwt = get_jwt(app_id)
        gh = gh_aiohttp.GitHubAPI(session, "lelelelelez")
        try:
            installation = await get_installation(gh, jwt, "lelelelelez")
        except ValueError as ve:
            print(ve)
        else:
            access_token = await get_installation_access_token(
                gh, jwt=jwt, installation_id=installation["id"]
            )
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(session, "lelelelelez",
                        oauth_token=access_token["token"]) 
        return gh
