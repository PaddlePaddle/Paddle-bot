import os
import aiohttp
import asyncio
import json
import datetime
import logging
import gidgethub
from utils.mail import Mail
from gidgethub import aiohttp as gh_aiohttp
from utils.auth import get_jwt, get_installation, get_installation_access_token

logging.basicConfig(
    level=logging.INFO,
    filename='./logs/regularClose.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        url = next_str[start_index + 1:end_index]
    else:
        url = None
    return url


async def overdueList(types, url, gh):
    today = datetime.date.today()
    lastYear = str(today - datetime.timedelta(days=365))
    logger.info("Close %s before %s" % (types, lastYear))
    overduelist = []
    while (url != None):
        (code, header, body) = await gh._request(
            "GET", url,
            {'accept': 'application/vnd.github.antiope-preview+json'})
        res = json.loads(body.decode('utf8'))
        for item in res:
            if types == 'issues' and 'pull_request' not in item:
                if item['updated_at'] < lastYear:  #if updateTime earlier than lastYear
                    user = item['user']['login']
                    comments_url = item['comments_url']
                    (code_co, header_co,
                     body_co) = await gh._request("GET", comments_url, {
                         'accept':
                         'application/vnd.github.antiope-preview+json'
                     })
                    comments = json.loads(body_co.decode('utf8'))
                    if len(comments) != 0:
                        last_comment_user = comments[len(comments) - 1][
                            'user']['login']
                        if last_comment_user != user:
                            overduelist.append(item['number'])
            elif types == 'pr':
                if item['updated_at'] < lastYear:  #if updateTime earlier than lastYear
                    overduelist.append(item['number'])
        url = getNextUrl(header['link'])
    return overduelist


async def close(types, itemList, gh, user, repo):
    if types == 'pr':
        event = 'pulls'
    else:
        event = 'issues'
    data = {"state": "closed"}
    d = json.dumps(data)
    logger.info("close %s count is %s: %s" % (types, len(itemList), itemList))
    if len(itemList) != 0:
        for i in itemList:
            url = "https://api.github.com/repos/%s/%s/%s/%s" % (user, repo,
                                                                event, i)
            try:
                await gh.patch(url, data=data)
                mail_content = "<html><body><p>Hi, ALL:</p> <p>以下issue/pr超过1年未更新，将关闭</p> <table border='1' align=center> <caption><font size='3'></font></caption>"
                mail_content = mail_content + "<tr align=center><td bgcolor='#d0d0d0'>类型</td><td bgcolor='#d0d0d0'>issue/pr号</td></tr>"
                task_info = ""
                task_info = task_info + "<tr align=center><td>{}</td><td>{}</td></tr>".format(
                    event, i)
                mail_content = mail_content + task_info + "</table></body></html>"
                sendCloseMail(mail_content)
                logger.info("%s_id: %s closed success!" % (event, i))
            except gidgethub.BadRequest:
                logger.error("%s_id: %s closed failed!" % (event, i))
    else:
        logger.info("%s is empty!" % item)


def sendCloseMail(content):
    mail = Mail()
    mail.set_sender('xxxx@baidu.com')
    mail.set_receivers(['xxxx@baidu.com'])
    mail.set_title('关闭超过1年未更新的issue/pr通知~')
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()


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
                gh, jwt=jwt, installation_id=installation["id"])
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(
                session, user, oauth_token=access_token["token"])
            pr_url = 'https://api.github.com/repos/%s/%s/pulls?per_page=100&page=1&direction=asc&q=addClass' % (
                user, repo)
            issues_url = 'https://api.github.com/repos/%s/%s/issues?per_page=100&page=1&direction=asc&q=addClass' % (
                user, repo)
            PRList = await overdueList('pr', pr_url, gh)
            logger.info("PRList: %s" % PRList)
            issueList = await overdueList('issues', issues_url, gh)
            logger.info("issueList: %s" % issueList)
            await close('pr', PRList, gh, user, repo)
            await close('issue', issueList, gh, user, repo)


def regularClose_job():
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main('PaddlePaddle', 'Paddle'))
