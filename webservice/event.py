from gidgethub import routing
from utils.check import checkPRCI, checkPRTemplate
from utils.readConfig import ReadConfig
import time
import logging

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
async def pull_request_event_ci(event, gh, repo, *args, **kwargs):
    """Check if PR triggers CI"""
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    commit_url = event.data["pull_request"]["commits_url"]
    sha = event.data["pull_request"]["head"]["sha"]
    if repo not in [
        'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
        'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    CHECK_CI = localConfig.cf.get(repo, 'CHECK_CI')
    if checkPRCI(commit_url, sha, CHECK_CI) == False:
        message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED_NOT_CI')
        logger.error("%s Not Trigger CI." % pr_num)
    else:
        message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED')
        logger.info("%s Trigger CI Successful." % pr_num)
    await gh.post(url, data={"body": message})


@router.register("status")
async def pull_request_ci_status(event, gh, repo, *args, **kwargs):
    """Check CI status, then post it"""
    comment_url = event.data["commit"]["comments_url"]
    commit_url = event.data["commit"]["url"]
    combined_statuses_url = commit_url + "/status"
    sha = event.data["sha"]
    short_sha = sha[0:7]
    if repo not in [
        'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
        'lelelelelez/leetcode'
    ]:
        repo = 'Others'
    if checkCIStatus(combined_statuses_url) == 0:
        message = localConfig.cf.get(repo, 'STATUS_CI_PENDING')
        logger.info("%s Still Pending" % short_sha)
    elif checkCIStatus(combined_statuses_url) == 1:
        message = localConfig.cf.get(repo, 'STATUS_CI_SUCCESS')
        logger.info("%s Passed All CI. " % short_sha)
    else:
        ci_failure = checkCIStatus(combined_statuses_url)
        error_message = checkCIDetail(commit_combined_ci_status, short_sha, ci_failure)
        message = localConfig.cf.get(repo, error_message)
        logger.error("%s Contains Failed CI" % short_sha)
    await gh.post(comment_url, data={"body": message})


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
