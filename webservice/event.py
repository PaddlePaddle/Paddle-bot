from gidgethub import routing
from utils.check import checkPRNotCI, checkPRTemplate, checkComments, checkCIState, getPRnum, ifCancelXly, getCommitComments
from utils.readConfig import ReadConfig
from utils.analyze_buildLog import ifDocumentFix, generateCiIndex, ifAlreadyExist, generateCiTime
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
async def pull_request_event_ci(event, gh, repo, *args, **kwargs):
    """Check if PR triggers CI"""
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    commit_url = event.data["pull_request"]["commits_url"]
    sha = event.data["pull_request"]["head"]["sha"]
    base_branch = event.data["pull_request"]['base']['label']
    if repo not in [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc'
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
            message = "Hi, This is a test PR and it will not trigger CI. If you want to trigger CI, please remove `notest` in your commit message."
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
            'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc'
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
            'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc'
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
            'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc'
    ]:
        repo = 'Others'
    if sender == 'paddle-bot[bot]':
        message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
        await gh.post(url, data={"body": message})


@router.register("issues", action="opened")
async def issues_assign_reviewer(event, gh, repo, *args, **kwargs):
    """assign reviewer for issuue"""
    if repo in ['PaddlePaddle/Paddle']:
        assign_url = event.data["issue"]["url"] + "/assignees"
        bos_url = 'https://paddle-docker-tar.cdn.bcebos.com/buildLog/todayDuty.log'  #取当日值班同学
        assignees = ['%s' % requests.get(bos_url).text]
        payload = {"assignees": assignees}
        response = await gh.post(assign_url, data=payload)
        assignees_length = len(response['assignees'])
        if assignees_length < 1:
            logger.error('%s not in PaddlePaddle!' % assignees)


@router.register("issues", action="opened")
async def issue_event_ci(event, gh, repo, *args, **kwargs):
    """Check if PR triggers CI"""
    issue_num = event.data['issue']['number']
    url = event.data["issue"]["comments_url"]
    if repo not in ['PaddlePaddle/Paddle', 'PaddlePaddle/benchmark', 'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc', 'iducn/HelloWorld']:
        repo = 'Others'
    if repo == 'PaddlePaddle/Paddle':
        message = "%s\r\n\r\n%s" % (localConfig.cf.get(repo, 'ISSUE_OPENED'),
                                    localConfig.cf.get(repo, 'ISSUE_OPENED_EN'))
        logger.info("Issue%s automatic reply successfully." % (issue_num))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})
    else:
        message = "%s\r\n\r\n%s" % (localConfig.cf.get(repo, 'ISSUE_OPENED'),
                                    localConfig.cf.get(repo, 'ISSUE_OPENED_EN'))
        logger.info("Issue%s automatic reply successfully." % (issue_num))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})


@router.register("issues", action="closed")
async def check_close_regularly(event, gh, repo, *args, **kwargs):
    """check_close_regularly"""
    url = event.data["issue"]["comments_url"]
    sender = event.data["sender"]["login"]
    if repo not in ['PaddlePaddle/Paddle', 'PaddlePaddle/benchmark', 'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc', 'iducn/HelloWorld']:
        repo = 'Others'
    if sender == 'paddle-bot[bot]':
        message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
        await gh.post(url, data={"body": message})
    else:
        message = "%s\r\n\r\n%s\r\n%s" % (localConfig.cf.get(repo, 'ISSUE_CLOSE'),
                                            localConfig.cf.get(repo, 'CHOOSE_YES'),
                                            localConfig.cf.get(repo, 'CHOOSE_NO'))
        await gh.post(url, data={"body": message})


@router.register("status")
async def check_ci_status(event, gh, repo, *args, **kwargs):
    """check_ci_status"""
    repo_just_xly_index_list = localConfig.cf.get(
        'ciIndex', 'repo_just_xly_index').split(
            ',')  #这些repo没有埋点，只能拿到xly传回的时间数据
    status_dict = {}
    state = event.data['state']
    commitId = event.data['sha']
    context = event.data['context']
    branch = event.data['repository']['default_branch']
    status_dict['commitId'] = commitId
    status_dict['ciName'] = context
    status_dict['repo'] = repo
    if state in ['success', 'failure']:
        commit_message = event.data['commit']['commit']['message']
        target_url = event.data['target_url']
        if target_url.startswith('https://xly.bce.baidu.com'):
            ifCancel = ifCancelXly(target_url)
            if ifCancel == True:
                logger.info("cancel xly: %s" % target_url)
            else:
                document_fix = ifDocumentFix(commit_message)
                if document_fix == True and context != "PR-CI-CPU-Py2":
                    EXCODE = 0
                elif repo in repo_just_xly_index_list:
                    EXCODE = 0 if state == 'success' else 1  #todo: branch now is default_branch
                else:
                    index_dict = generateCiIndex(repo, commitId, target_url)
                    logger.info("target_url: %s" % target_url)
                    logger.info("index_dict: %s" % index_dict)
                    EXCODE = index_dict['EXCODE']
                    branch = index_dict['branch']
                ifInsert = True
                status_dict['branch'] = branch
                status_dict['status'] = state
                status_dict['documentfix'] = '%s' % document_fix
                status_dict['EXCODE'] = EXCODE
                insertTime = int(time.time())
                query_stat = "SELECT * FROM paddle_ci_status WHERE ciName='%s' and commitId='%s' and status='%s' order by time desc" % (
                    status_dict['ciName'], status_dict['commitId'],
                    status_dict['status'])
                queryTime = ifAlreadyExist(query_stat)
                if queryTime != '':
                    ifInsert = False if insertTime - queryTime < 30 else True
                    logger.error("%s already insert!" % status_dict)
                if ifInsert == True:
                    time_dict = generateCiTime(target_url)
                    for key in time_dict:
                        status_dict[key] = time_dict[key]
                    logger.info("status_dict: %s" % status_dict)
                    db = Database()
                    result = db.insert('paddle_ci_status', status_dict)
                    if result == True:
                        logger.info('%s %s insert paddle_ci_status success!' %
                                    (context, commitId))
                    else:
                        logger.error('%s %s insert paddle_ci_status failed!' %
                                     (context, commitId))
        else:
            logger.info(' %s ❎Not Support Teamcity CI!' % status_dict)


@router.register("status")
async def check_ci_failure(event, gh, repo, *args, **kwargs):
    """check commits whether passed all CI or contain failed CI"""
    if repo in ['PaddlePaddle/Paddle', 'PaddlePaddle/benchmark']:
        state = event.data['state']
        context = event.data['context']
        commit_url = event.data["commit"]["url"]
        combined_statuses_url = commit_url + "/status"
        comment_url = event.data["commit"]["comments_url"]
        ci_link = event.data['target_url']
        ifCancel = ifCancelXly(ci_link)
        if ifCancel == True:
            logger.info("cancel ci_link: %s" % ci_link)
        else:
            commitId = event.data['sha']
            shortId = commitId[0:7]
            pr_search_url = "https://api.github.com/search/issues?q=sha:" + commitId
            required_ci_list = localConfig.cf.get(repo, 'REQUIRED_CI')
            sender = event.data['commit']['author']['login']
            if sender in [
                    'lelelelelez', 'randytli', 'lanxianghit', 'zhiqiu',
                    'chenwhql', 'GaoWei8', 'gfwm2013', 'phlrain', 'Xreki',
                    'liym27', 'luotao1', 'pangyoki', 'tianshuo78520a', 'iducn',
                    'feng626', 'wangchaochaohu', 'wanghuancoder', 'wzzju',
                    'joejiong', 'Aurelius84', 'zhangting2020', 'zhhsplendid',
                    'zhouwei25'
            ]:
                pr_num = getPRNum(pr_search_url)
                commits_url = "https://api.github.com/repos/" + repo + "/pulls/" + str(
                    pr_num) + "/commits?per_page=250"
                comment_list = checkComments(comment_url)
                combined_ci_status, required_all_passed = await checkCIState(
                    combined_statuses_url, required_ci_list)
                if state in ['success', 'failure', 'error']:
                    if state == 'success':
                        if combined_ci_status != 'success':
                            await update_ci_failure_summary(
                                gh, context, ci_link, comment_list, pr_num,
                                shortId)
                        if combined_ci_status == 'success' or required_all_passed is True:
                            if len(comment_list) == 0:
                                message = localConfig.cf.get(
                                    repo, 'STATUS_CI_SUCCESS')
                                logger.info(
                                    "Successful trigger logic for CREATE success comment: %s; sha: %s"
                                    % (pr_num, shortId))
                                await gh.post(
                                    comment_url, data={"body": message})
                                await clean_parent_comment_list(
                                    gh, commits_url, pr_num, shortId)
                            else:
                                for i in range(len(comment_list)):
                                    comment_sender = comment_list[i]['user'][
                                        'login']
                                    comment_body = comment_list[i]['body']
                                    update_url = comment_list[i]['url']
                                    if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                                            '## 🕵️'):
                                        update_message = localConfig.cf.get(
                                            repo, 'STATUS_CI_SUCCESS')
                                        logger.info(
                                            "Successful trigger logic for CORRECT failed comment: %s; sha: %s"
                                            % (pr_num, shortId))
                                        await gh.delete(update_url)
                                        await gh.post(
                                            comment_url,
                                            data={"body": update_message})
                    else:
                        await create_add_ci_failure_summary(
                            gh, context, comment_url, ci_link, shortId, pr_num,
                            comment_list, commits_url)


async def create_add_ci_failure_summary(gh, context, comment_url, ci_link,
                                        shortId, pr_num, comment_list,
                                        commits_url):
    """gradually find failed CI"""
    hyperlink_format = '<a href="{link}">{text}</a>'
    failed_header = "## 🕵️ CI failures summary\r\n"
    failed_template = "🔍 PR: <b>#" + str(
        pr_num) + "</b> Commit ID: <b>%s</b> contains failed CI.\r\n"
    failed_ci_bullet = "- <b>Failed: %s</b>"
    failed_ci_hyperlink = hyperlink_format.format(link=ci_link, text=context)
    if len(comment_list) == 0:
        if ci_link.startswith('https://xly.bce.baidu.com'):
            error_message = failed_header + failed_template % str(
                shortId) + failed_ci_bullet % failed_ci_hyperlink
            logger.info(
                "Successful trigger logic for CREATE XLY bullet. pr num: %s; sha: %s"
                % (pr_num, shortId))
            await gh.post(comment_url, data={"body": error_message})
            await clean_parent_comment_list(gh, commits_url, pr_num, shortId)
        else:
            error_message = failed_header + failed_template % str(
                shortId) + failed_ci_bullet % context
            logger.info(
                "Successful trigger logic for CREATE TC bullet. pr num: %s; sha: %s"
                % (pr_num, shortId))
            await gh.post(comment_url, data={"body": error_message})
            await clean_parent_comment_list(gh, commits_url, pr_num, shortId)
    else:
        logger.info("comment_list: %s" % comment_list)
        for i in range(len(comment_list)):
            comment_sender = comment_list[i]['user']['login']
            comment_body = comment_list[i]['body']
            update_url = comment_list[i]['url']
            if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                    '## 🕵️'):
                split_body = comment_body.split("\r\n")
                context_list = re.findall(r"\">(.+?)</a></b>", comment_body)
                if ci_link.startswith('https://xly.bce.baidu.com'):
                    IsExit = True
                    for j in range(len(context_list)):
                        logger.info("context:%s" % context)
                        if context == context_list[j]:
                            IsExit = False
                            latest_body = comment_body.replace(
                                "\r\n" + split_body[j + 2], '')
                            update_message = latest_body + "\r\n" + failed_ci_bullet % failed_ci_hyperlink
                            logger.info(
                                "Successful trigger logic for REMOVING and ADDING XLY bullet. pr num: %s; sha: %s"
                                % (pr_num, shortId))
                            await gh.patch(
                                update_url, data={"body": update_message})
                    if IsExit is True:
                        update_message = comment_body + "\r\n" + failed_ci_bullet % failed_ci_hyperlink
                        logger.info(
                            "Successful trigger logic for ADDING XLY bullet. pr num: %s; sha: %s"
                            % (pr_num, shortId))
                        logger.info("update_message: %s" % update_message)
                        await gh.patch(
                            update_url, data={"body": update_message})
                else:
                    corrected_ci = failed_ci_bullet % context
                    if corrected_ci in split_body:
                        latest_body = comment_body.replace(
                            "\r\n" + corrected_ci, '')
                        update_message = latest_body + "\r\n" + failed_ci_bullet % context
                        logger.info(
                            "Successful trigger logic for ADDING TC bullet. pr num: %s; sha: %s"
                            % (pr_num, shortId))
                        await gh.patch(
                            update_url, data={"body": update_message})
                    else:
                        update_message = comment_body + "\r\n" + failed_ci_bullet % context
                        await gh.patch(
                            update_url, data={"body": update_message})
            elif comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                    '✅️'):
                if ci_link.startswith('https://xly.bce.baidu.com'):
                    update_message = failed_header + failed_template % str(
                        shortId) + failed_ci_bullet % failed_ci_hyperlink
                    logger.info(
                        "Successful trigger logic for CHANGE Success Comment to XLY bullet. pr num: %s; sha: %s"
                        % (pr_num, shortId))
                    await gh.delete(update_url)
                    await gh.post(comment_url, data={"body": update_message})
                else:
                    update_message = failed_header + failed_template % str(
                        shortId) + failed_ci_bullet % context
                    logger.info(
                        "Successful trigger logic for CHANGE Success Comment to TC bullet. pr num: %s; sha: %s"
                        % (pr_num, shortId))
                    await gh.delete(update_url)
                    await gh.post(comment_url, data={"body": update_message})


async def update_ci_failure_summary(gh, context, ci_link, comment_list,
                                    pr_num):
    """erase corrected CI"""
    failed_ci_bullet = "- <b>Failed: %s</b>"
    for i in range(len(comment_list)):
        comment_sender = comment_list[i]['user']['login']
        comment_body = comment_list[i]['body']
        update_url = comment_list[i]['url']
        if comment_sender == "paddle-bot[bot]" and comment_body.startswith(
                '## 🕵️'):
            split_body = comment_body.split("\r\n")
            context_list = re.findall(r"\">(.+?)</a></b>", comment_body)
            if ci_link.startswith('https://xly.bce.baidu.com'):
                for j in range(len(context_list)):
                    if context == context_list[j]:
                        update_message = comment_body.replace(
                            "\r\n" + split_body[j + 2], '')
                        curr_split_body = update_message.split("\r\n")
                        if len(curr_split_body) > 2:
                            logger.info(
                                "Successful trigger logic for ERASE corrected XLY bullet. pr num: %s; sha: %s"
                                % (pr_num, shortId))
                            await gh.patch(
                                update_url, data={"body": update_message})
                        else:
                            logger.info(
                                "ERASE ALL comment as NO bullet left after erase last XLY bullet. pr num: %s; sha: %s"
                                % (pr_num, shortId))
                            await gh.delete(update_url)
            else:
                corrected_ci = failed_ci_bullet % context
                if corrected_ci in split_body:
                    update_message = comment_body.replace(
                        "\r\n" + corrected_ci, '')
                    curr_split_body = update_message.split("\r\n")
                    if len(curr_split_body) > 2:
                        logger.info(
                            "Successful trigger logic for ERASE corrected TC bullet. pr num: %s; sha: %s"
                            % (pr_num, shortId))
                        await gh.patch(
                            update_url, data={"body": update_message})
                    else:
                        logger.info(
                            "ERASE ALL comment as NO bullet left after erase last TC bullet. pr num: %s; sha: %s"
                            % (pr_num, shortId))
                        await gh.delete(update_url)


async def clean_parent_comment_list(gh, commits_url, pr_num, shortId):
    commits_comments_list = getCommitComments(commits_url)
    if len(commits_comments_list) > 1:  #pr中有大于一条commit再执行判断
        for i in range(len(commits_comments_list) - 1):  #最新commit不需要清理
            commit_comments_list = commits_comments_list[i]
            if len(commit_comments_list) != 0:
                count = 0
                for j in range(len(commit_comments_list)):
                    comment_sender = commit_comments_list[j]['user']['login']
                    if comment_sender == "paddle-bot[bot]":
                        delete_url = commit_comments_list[j]['url']
                        delete_sha = commit_comments_list[j]['commit_id'][0:7]
                        count += 1
                        logger.info(
                            "REMOVE: %s comment(s) from parent commit: %s; pr num: %s; current sha: %s"
                            % (count, delete_sha, pr_num, shortId))
                        await gh.delete(delete_url)
                    else:
                        logger.info("Comment from User: %s, stop cleaning." %
                                    comment_sender)
