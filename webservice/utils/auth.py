import os
import time
import jwt
import aiohttp
from gidgethub import aiohttp as gh_aiohttp


def get_jwt(app_id):
    # TODO: read is as an environment variable
    path_to_private_key = os.getenv("PEM_FILE_PATH")
    pem_file = open(path_to_private_key, "rt").read()
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),
        "iss": app_id,
    }
    encoded = jwt.encode(payload, pem_file, algorithm="RS256")
    bearer_token = encoded.decode("utf-8")

    return bearer_token


async def get_installation(gh, jwt, username):
    async for installation in gh.getiter(
        "/app/installations",
        jwt=jwt,
        accept="application/vnd.github.machine-man-preview+json", ):
        if installation["account"]["login"] == username:
            return installation

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
        accept="application/vnd.github.machine-man-preview+json", )
    return response


async def Github_APP_Auth():
    async with aiohttp.ClientSession() as session:
        app_id = os.getenv("GH_APP_ID")
        jwt = get_jwt(app_id)
        gh = gh_aiohttp.GitHubAPI(session, "lelelelelez")
        try:
            installation = await get_installation(gh, jwt, "lelelelelez")
        except ValueError as ve:
            print(ve)
        else:
            access_token = await get_installation_access_token(
                gh, jwt=jwt, installation_id=installation["id"])
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(
                session, "lelelelelez", oauth_token=access_token["token"])
        return gh
