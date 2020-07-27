from gidgethub import routing
from utils.check import checkPRNotCI, checkPRTemplate, checkComments, checkCIState
from utils.readConfig import ReadConfig
from utils.analyze_buildLog import ifDocumentFix, generateCiIndex, ifAlreadyExist
from utils.db import Database
from utils.convert import javaTimeTotimeStamp
import time
import logging
import re
router = routing.Router()
localConfig = ReadConfig()

logging.basicConfig(
    level=logging.INFO,
    filename='./logs/event.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_check_run(sha, gh, repo):
    """create a checkrun to check PR's description"""
    data = {'name': 'CheckPRTemplate', 'head_sha': sha}
    url = 'https://api.github.com/repos/%s/check-runs' % repo
    await gh.post(
        url, data=data, accept='application/vnd.github.antiope-preview+json')


@router.register("pull_request", action="opened")
@router.register("pull_request", action="synchronize")
async def get_commitCreateTime(event, gh, repo, *args, **kwargs):
    "Get commit CreateTime"
    create_dict = {}
    create_dict['repo'] = repo
    pr_num = event.data['number']
    sha = event.data["pull_request"]["head"]["sha"]
    create_dict['PR'] = pr_num
    create_dict['commitId'] = sha
    if event.data['action'] == "opened":
        CreateTime = event.data["pull_request"]["created_at"]
    elif event.data['action'] == "synchronize":
        CreateTime = event.data["pull_request"]["updated_at"]
    createTime = javaTimeTotimeStamp(CreateTime)
    create_dict['createTime'] = createTime
    db = Database()
    result = db.insert('commit_create_time', create_dict)
    if result == True:
        logger.info('%s %s insert commit_create_time success: %s!' %
                    (pr_num, sha, createTime))
    else:
        logger.error('%s %s insert commit_create_time failed: %s!' %
                     (pr_num, sha, createTime))


@router.register("pull_request", action="opened")
@router.register("pull_request", action="synchronize")
async def pull_request_event_ci(event, gh, repo, *args, **kwargs):
    """Check if PR triggers CI"""
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    commit_url = event.data["pull_request"]["commits_url"]
    sha = event.data["pull_request"]["head"]["sha"]
    base_branch = event.data["pull_request"]['base']['label']
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    if base_branch.startswith(
            'PaddlePaddle:release') and repo == 'PaddlePaddle/Paddle':
        message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED')
        logger.info("%s_%s Trigger CI Successful." % (pr_num, sha))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})
    else:
        if checkPRNotCI(commit_url, sha) == False:
            message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED')
            logger.info("%s_%s Trigger CI Successful." % (pr_num, sha))
        else:
            message = "Hi, It's a test PR, it will not trigger CI. If you want to trigger CI, please remove `notest` in your commit message."
            logger.info("%s_%s is a test PR." % (pr_num, sha))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})


@router.register("pull_request", action="synchronize")
@router.register("pull_request", action="edited")
@router.register("pull_request", action="opened")
async def pull_request_event_template(event, gh, repo, *args, **kwargs):
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    BODY = event.data["pull_request"]["body"]
    sha = event.data["pull_request"]["head"]["sha"]
    await create_check_run(sha, gh, repo)
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    CHECK_TEMPLATE = localConfig.cf.get(repo, 'CHECK_TEMPLATE')
    global check_pr_template
    global check_pr_template_message
    check_pr_template, check_pr_template_message = checkPRTemplate(
        repo, BODY, CHECK_TEMPLATE)
    if check_pr_template == False:
        message = localConfig.cf.get(repo, 'NOT_USING_TEMPLATE')
        logger.error("%s Not Follow Template." % pr_num)
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})
    else:
        comment_list = checkComments(url)
        for i in range(len(comment_list)):
            comment_sender = comment_list[i]['user']['login']
            comment_body = comment_list[i]['body']
            if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                    '❌'):
                message = localConfig.cf.get(repo, 'PR_CORRECT_DESCRIPTION')
                logger.info("%s Correct PR Description and Meet Template" %
                            pr_num)
                update_url = comment_list[i]['url']
                await gh.patch(update_url, data={"body": message})


@router.register("check_run", action="created")
async def running_check_run(event, gh, repo, *args, **kwargs):
    """running checkrun"""
    url = event.data["check_run"]["url"]
    name = event.data["check_run"]["name"]
    data = {"name": name, "status": "in_progress"}
    await gh.patch(
        url, data=data, accept='application/vnd.github.antiope-preview+json')
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    if check_pr_template == False:
        error_message = check_pr_template_message if check_pr_template_message != '' else localConfig.cf.get(
            repo, 'NOT_USING_TEMPLATE')
        data = {
            "name": name,
            "status": "completed",
            "conclusion": "failure",
            "output": {
                "title": "checkTemplateFailed",
                "summary": error_message
            }
        }
    else:
        data = {
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "output": {
                "title": "checkTemplateSuccess",
                "summary":
                "✅ This PR's description meets the template requirements!"
            }
        }
    await gh.patch(
        url, data=data, accept='application/vnd.github.antiope-preview+json')


@router.register("pull_request", action="closed")
async def check_close_regularly(event, gh, repo, *args, **kwargs):
    """check_close_regularly"""
    url = event.data["pull_request"]["comments_url"]
    sender = event.data["sender"]["login"]
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    if sender == 'paddle-bot[bot]':
        message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
        await gh.post(url, data={"body": message})


@router.register("issues", action="closed")
async def check_close_regularly(event, gh, repo, *args, **kwargs):
    """check_close_regularly"""
    url = event.data["issue"]["comments_url"]
    sender = event.data["sender"]["login"]
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    if sender == 'paddle-bot[bot]':
        message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
        await gh.post(url, data={"body": message})


@router.register("status")
async def check_ci_status(event, gh, repo, *args, **kwargs):
    """check_ci_status"""
    if repo in ['PaddlePaddle/Paddle']:
        status_dict = {}
        state = event.data['state']
        commitId = event.data['sha']
        context = event.data['context']
        status_dict['commitId'] = commitId
        status_dict['ciName'] = context
        shortId = commitId[0:7]
        if state == 'success':
            commit_message = event.data['commit']['commit']['message']
            document_fix = ifDocumentFix(commit_message)
            if document_fix == False:
                target_url = event.data['target_url']
                generateCiIndex(repo, commitId, target_url)
        else:
            print("commitID: %s" % shortId)
            print("state : %s" % state)
        if state in ['success', 'failure']:
            ifInsert = True
            status_dict['status'] = state
            insertTime = int(time.time())
            query_stat = "SELECT * FROM paddle_ci_status WHERE ciName='%s' and commitId='%s' and status='%s' order by time desc" % (
                status_dict['ciName'], status_dict['commitId'],
                status_dict['status'])
            queryTime = ifAlreadyExist(query_stat)
            if queryTime != '':
                ifInsert = False if insertTime - queryTime < 30 else True
            if ifInsert == True:
                db = Database()
                result = db.insert('paddle_ci_status', status_dict)
                if result == True:
                    logger.info('%s %s insert paddle_ci_status success!' %
                                (context, commitId))
                else:
                    logger.error('%s %s insert paddle_ci_status failed!' %
                                 (context, commitId))


@router.register("status")
async def failed_ci_detector(event, gh, repo, *args, **kwargs):
    """when find failed ci/passed all ci, make comment"""
    if repo in ['PaddlePaddle/Paddle']:
        state = event.data['state']
        commitId = event.data['sha']
        context = event.data['context']
        shortId = commitId[0:7]
        comment_url = event.data["commit"]["comments_url"]
        commit_url = event.data["commit"]["url"]
        combined_statuses_url = commit_url + "/status"
        ci_link = event.data['target_url']
        hyperlink_format = '<a href="{link}">{text}</a>'
        failed_template = "🕵️Commit ID: <b>%s</b> contains failed CI.\r\n"
        xly_template = "<b>🔍Failed: </b>"
        tc_template = "<b>🔍Failed: %s</b>"
        failed_ci_hyperlink = hyperlink_format.format(
            link=ci_link, text=context)
        comment_list = checkComments(comment_url)
        combined_ci_status = checkCIState(combined_statuses_url)
        if state in ['success', 'failure', 'error']:
            if state == 'success':
                if combined_ci_status == 'success':
                    if comment_list == '[]':
                        message = localConfig.cf.get(repo, 'STATUS_CI_SUCCESS')
                        await gh.post(comment_url, data={"body": message})
                    else:
                        for i in range(len(comment_list)):
                            comment_sender = comment_list[i]['user']['login']
                            comment_body = comment_list[i]['body']
                            update_url = comment_list[i]['url']
                            if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                                    '🕵️'):
                                update_message = localConfig.cf.get(
                                    repo, 'STATUS_CI_SUCCESS')
                                await gh.patch(
                                    update_url, data={"body": update_message})
                            else:
                                message = localConfig.cf.get(
                                    repo, 'STATUS_CI_SUCCESS')
                                await gh.post(
                                    comment_url, data={"body": message})
                elif combined_ci_status == 'failure':
                    for i in range(len(comment_list)):
                        comment_sender = comment_list[i]['user']['login']
                        comment_body = comment_list[i]['body']
                        update_url = comment_list[i]['url']
                        if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                                '🕵️'):
                            latest_comment = comment_list[i]
                            latest_body = latest_comment['body']
                            split_body = latest_body.split("\r\n")
                            if ci_link.startswith('https://xly.bce.baidu.com'):
                                corrected_ci = xly_template + failed_ci_hyperlink
                                if corrected_ci in split_body:
                                    update_message = re.sub(
                                        "\r\n" + corrected_ci, '', latest_body)
                                    await gh.patch(
                                        update_url,
                                        data={"body": update_message})
                            else:
                                corrected_ci = tc_template % context
                                if corrected_ci in split_body:
                                    update_message = re.sub(
                                        "\r\n" + corrected_ci, '', latest_body)
                                    await gh.patch(
                                        update_url,
                                        data={"body": update_message})
            else:
                if comment_list == '[]':
                    if ci_link.startswith('https://xly.bce.baidu.com'):
                        error_message = failed_template % str(
                            shortId) + xly_template + failed_ci_hyperlink
                        await gh.post(
                            comment_url, data={"body": error_message})
                    else:
                        error_message = failed_template % str(
                            shortId) + tc_template % context
                        await gh.post(
                            comment_url, data={"body": error_message})
                else:
                    for i in range(len(comment_list)):
                        comment_sender = comment_list[i]['user']['login']
                        comment_body = comment_list[i]['body']
                        if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                                '🕵️'):
                            latest_comment = comment_list[i]
                            latest_body = latest_comment['body']
                            update_url = latest_comment['url']
                            if ci_link.startswith('https://xly.bce.baidu.com'):
                                update_message = latest_body + "\r\n" + xly_template + failed_ci_hyperlink
                                await gh.patch(
                                    update_url, data={"body": update_message})
                            else:
                                update_message = latest_body + "\r\n" + tc_template % context
                                await gh.patch(
                                    update_url, data={"body": update_message})
