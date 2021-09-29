from gidgethub import routing
from utils.check import checkPRNotCI, checkPRTemplate, checkComments, checkCIState, getPRnum, ifCancelXly, getCommitComments, xlyJob
from utils.readConfig import ReadConfig
from utils.analyze_buildLog import ifDocumentFix, ifAlreadyExist, analysisBuildLog
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
    pr_effect_repos = localConfig.cf.get('FunctionScope', 'PR_checkTemplate')
    if repo in pr_effect_repos:
        pr_num = event.data['number']
        url = event.data["pull_request"]["comments_url"]
        BODY = event.data["pull_request"]["body"]
        sha = event.data["pull_request"]["head"]["sha"]
        await create_check_run(sha, gh, repo)
        CHECK_TEMPLATE = localConfig.cf.get(repo, 'CHECK_TEMPLATE')
        global check_pr_template
        global check_pr_template_message
        check_pr_template, check_pr_template_message = checkPRTemplate(
            repo, BODY, CHECK_TEMPLATE)
        logger.info("check_pr_template: %s pr: %s" %
                    (check_pr_template, pr_num))
        comment_list = checkComments(url)
        if check_pr_template == False:
            message = localConfig.cf.get(repo, 'NOT_USING_TEMPLATE')
            logger.error("%s Not Follow Template." % pr_num)
            if event.data['action'] == "opened":
                await gh.post(url, data={"body": message})
            else:
                for i in range(len(comment_list)):
                    comment_sender = comment_list[i]['user']['login']
                    comment_body = comment_list[i]['body']
                    if comment_sender in [
                            "paddle-bot[bot]", "just-test-paddle[bot]"
                    ] and comment_body.startswith('✅ This PR'):
                        message = localConfig.cf.get(repo,
                                                     'NOT_USING_TEMPLATE')
                        logger.error(
                            "%s Not follow template, send notification." %
                            pr_num)
                        update_url = comment_list[i]['url']
                        await gh.patch(update_url, data={"body": message})
        else:
            for i in range(len(comment_list)):
                comment_sender = comment_list[i]['user']['login']
                comment_body = comment_list[i]['body']
                if comment_sender in [
                        "paddle-bot[bot]", "just-test-paddle[bot]"
                ] and comment_body.startswith('❌ The PR'):
                    message = localConfig.cf.get(repo,
                                                 'PR_CORRECT_DESCRIPTION')
                    logger.info("%s Correct PR Description and Meet Template" %
                                pr_num)
                    update_url = comment_list[i]['url']
                    await gh.patch(update_url, data={"body": message})


@router.register("check_run", action="created")
async def running_check_run(event, gh, repo, *args, **kwargs):
    """running checkrun"""
    url = event.data["check_run"]["url"]
    name = event.data["check_run"]["name"]
    if name == 'CheckPRTemplate':
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
                    "✅ This PR's description meets the tempate requirements!"
                }
            }
        logger.info(data)
        await gh.patch(
            url,
            data=data,
            accept='application/vnd.github.antiope-preview+json')


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
    today = datetime.date.today()
    issue_effect_repos = localConfig.cf.get('FunctionScope',
                                            'ISSUE_open_assign_reviewer')
    if repo in issue_effect_repos:
        assign_url = event.data["issue"]["url"] + "/assignees"
        f = open("buildLog/%s_todayDuty-%s.log" % (repo.split('/')[-1], today))
        assignees = f.read().strip()
        payload = {"assignees": ['%s' % assignees]}
        logger.info("payload: %s" % payload)
        response = await gh.post(assign_url, data=payload)
        logger.info("response['assignees']:  %s" % response['assignees'])
        assignees_length = len(response['assignees'])
        if assignees_length < 1:
            logger.error('%s not in PaddlePaddle!' % assignees)
        f.close()


@router.register("issues", action="opened")
async def issue_event(event, gh, repo, *args, **kwargs):
    """Automatically respond to users"""
    issue_effect_repos = localConfig.cf.get('FunctionScope',
                                            'ISSUE_open_auto_reply')
    if repo in issue_effect_repos:
        issue_num = event.data['issue']['number']
        url = event.data["issue"]["comments_url"]
        message = "%s\r\n\r\n%s" % (localConfig.cf.get(
            repo, 'ISSUE_OPENED_CN'), localConfig.cf.get(repo,
                                                         'ISSUE_OPENED_EN'))
        logger.info("%s Issue %s automatic reply successfully." %
                    (repo, issue_num))
        await gh.post(url, data={"body": message})


@router.register("issues", action="closed")
async def check_close_regularly(event, gh, repo, *args, **kwargs):
    """check_close_regularly"""
    issue_effect_repos = localConfig.cf.get('FunctionScope',
                                            'ISSUE_close_auto_reply')
    if repo in issue_effect_repos:
        url = event.data["issue"]["comments_url"]
        sender = event.data["sender"]["login"]
        if sender == 'paddle-bot[bot]':
            message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
            await gh.post(url, data={"body": message})
        else:
            message = "%s\r\n\r\n%s\r\n%s" % (localConfig.cf.get(
                repo, 'ISSUE_CLOSE'), localConfig.cf.get(
                    repo, 'CHOOSE_YES'), localConfig.cf.get(repo, 'CHOOSE_NO'))
            await gh.post(url, data={"body": message})


#PR的CI数据采集
@router.register("status")
async def get_ci_index(event, gh, repo, *args, **kwargs):
    """get_ci_index"""
    target_url = event.data['target_url']
    if target_url.startswith('https://xly.bce.baidu.com') and event.data[
            'state'] in ['success', 'failure']:
        db = Database()
        task = xlyJob()
        mark_ci_by_bot = task.MarkByPaddleBot(target_url)  #判断是否是机器人标记
        if mark_ci_by_bot == False:  #不是被标记的
            ##基础指标
            basic_ci_index_dict = {}
            state = event.data['state']
            commitId = event.data['sha']
            ciName = event.data['context']
            triggerUser = event.data['commit']['commit']['committer']['name']
            basic_ci_index_dict['ciName'] = ciName
            basic_ci_index_dict['commitId'] = commitId
            basic_ci_index_dict['status'] = state
            basic_ci_index_dict['repo'] = repo
            basic_ci_index_dict['triggerUser'] = triggerUser
            ifCancel = task.CancelJobByXly(target_url)
            if ifCancel == False:  #CI被取消的不写入数据库
                if repo not in ['PaddlePaddle/Paddle']:  #没有test=documentfix的情况
                    document_fix = 'False'
                    basic_ci_index_dict[
                        'EXCODE'] = 0 if state == 'success' else 1  #非Paddle的退出码只有0, 1
                else:
                    commit_message = event.data['commit']['commit']['message']
                    document_fix = ifDocumentFix(commit_message)
                basic_ci_index_dict['documentfix'] = '%s' % document_fix
                if 'iscan' in ciName.lower():
                    basic_ci_index_dict[
                        'EXCODE'] = 0 if state == 'success' else 1
                else:
                    analysis_Log_object = analysisBuildLog(repo, commitId,
                                                           target_url)
                    timeciindex = analysis_Log_object.getBasicCIIndex(
                        document_fix)
                    for key in timeciindex:
                        basic_ci_index_dict[key] = timeciindex[key]
                ifInsert = False  #查询30s内是否已经插入数据了
                insertTime = int(time.time())
                query_stat = "SELECT * FROM paddle_ci_status WHERE ciName='%s' and commitId='%s' and status='%s' order by time desc" % (
                    basic_ci_index_dict['ciName'],
                    basic_ci_index_dict['commitId'],
                    basic_ci_index_dict['status'])
                queryTime_status = ifAlreadyExist(query_stat)
                if queryTime_status != '':
                    ifInsert = True if insertTime - queryTime_status < 30 else False
                if ifInsert == False:
                    logger.info("basic_ci_index: %s" % basic_ci_index_dict)
                    result = db.insert('paddle_ci_status', basic_ci_index_dict)
                    if result == True:
                        logger.info('%s %s insert paddle_ci_status success!' %
                                    (ciName, commitId))
                    else:
                        logger.error('%s %s insert paddle_ci_status failed!' %
                                     (ciName, commitId))

                #采集详细指标
                if repo in ['PaddlePaddle/Paddle']:
                    Paddle_sa_detailed_ci_tuple = tuple(
                        localConfig.cf.get('CIIndexScope',
                                           'Paddle_sa_detailed_ci').split(','))
                    Paddle_container_detailed_ci_tuple = tuple(
                        localConfig.cf.get('CIIndexScope',
                                           'Paddle_container_detailed_ci')
                        .split(','))
                    if ciName.startswith(Paddle_container_detailed_ci_tuple
                                         ) or ciName.startswith(
                                             Paddle_sa_detailed_ci_tuple):
                        detailed_ci_index_dict = analysis_Log_object.getDetailsCIIndex(
                            basic_ci_index_dict)
                        logger.info("detailed_ci_index: %s" %
                                    detailed_ci_index_dict)
                        insertTime = int(time.time())
                        query_stat = "SELECT * FROM paddle_ci_index WHERE ciName='%s' and commitId='%s' and PR=%s order by time desc" % (
                            detailed_ci_index_dict['ciName'],
                            detailed_ci_index_dict['commitId'],
                            detailed_ci_index_dict['PR'])
                        queryTime_index = ifAlreadyExist(query_stat)

                        if queryTime_index != '':
                            ifInsert = False if insertTime - queryTime_index < 30 else True
                        if ifInsert == False:
                            result = db.insert('paddle_ci_index',
                                               detailed_ci_index_dict)
                            if result == True:
                                logger.info(
                                    '%s %s %s insert paddle_ci_index success!'
                                    % (ciName, detailed_ci_index_dict['PR'],
                                       commitId))
                            else:
                                logger.info(
                                    '%s %s %s insert paddle_ci_index failed!' %
                                    (ciName, detailed_ci_index_dict['PR'],
                                     commitId))


async def clean_parent_comment_list(gh, commits_url, pr_num, shortId):
    commits_comments_list = getCommitComments(commits_url)
    if len(commits_comments_list) > 1:  # pr中有大于一条commit再执行判断
        for i in range(len(commits_comments_list) - 1):  # 最新commit不需要清理
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


@router.register("status")
async def my_check_ci_failure(event, gh, repo, *args, **kwargs):
    """check commits whether passed all CI or contain failed CI"""
    print('my_check_ci_failure')
    # print('repo:', repo)
    # print('event.data:', event.data)
    if repo in ['PaddlePaddle/Paddle', 'PaddlePaddle/Paddle-bot'
                ] and event.data[
                    'state'] in ['success', 'failure', 'error'] and event.data[
                        'target_url'].startswith('https://xly.bce.baidu.com'):
        triggerUser = event.data['commit']['commit']['committer']['name']
        if triggerUser not in ['lelelelelez', 'Jiangxinz']:
            return
        logger.info('trigger by %s' % (triggerUser))
        state = event.data['state']
        context = event.data['context']
        commit_url = event.data["commit"]["url"]
        combined_statuses_url = commit_url + "/status"
        comment_url = event.data["commit"]["comments_url"]
        parent_url = event.data['commit']['parents'][0]['url']
        parent_comment_url = parent_url + "/comments"
        ci_link = event.data['target_url']
        task = xlyJob()
        mark_ci_by_bot = task.MarkByPaddleBot(ci_link)
        ifCancel = task.CancelJobByXly(ci_link)
        bot_name = 'just-test-paddle[bot]'
        if mark_ci_by_bot == True:
            logger.info("mark ci by paddle-bot: %s" % ci_link)
        elif ifCancel == True:
            logger.info("cancel ci_link: %s" % ci_link)
        else:
            commitId = event.data['sha']
            shortId = commitId[0:7]
            pr_search_url = "https://api.github.com/search/issues?q=sha:" + commitId
            required_ci_list = localConfig.cf.get(repo, 'REQUIRED_CI')
            PR = getPRNum(pr_search_url)
            commits_url = "https://api.github.com/repos/" + repo + "/pulls/" + str(
                PR) + "/commits?per_page=250"
            comment_list = checkComments(comment_url)
            combined_ci_status, required_all_passed = await checkCIState(
                combined_statuses_url, required_ci_list)
            if state in ['success', 'failure', 'error']:
                if state == 'success':
                    if combined_ci_status != 'success':
                        await my_update_ci_failure_summary(
                            gh, context, ci_link, comment_list, PR, shortId)
                    if combined_ci_status == 'success' or required_all_passed is True:
                        if len(comment_list) == 0:
                            message = localConfig.cf.get(repo,
                                                         'STATUS_CI_SUCCESS')
                            logger.info(
                                "Successful trigger logic for CREATE success comment: %s; sha: %s"
                                % (PR, shortId))
                            await gh.post(comment_url, data={"body": message})
                            await clean_parent_comment_list(gh, commits_url,
                                                            PR, shortId)
                        else:
                            for i in range(len(comment_list)):
                                comment_sender = comment_list[i]['user'][
                                    'login']
                                comment_body = comment_list[i]['body']
                                update_url = comment_list[i]['url']

                                if comment_sender == bot_name and comment_body.startswith(
                                        '## 🕵️'):
                                    update_message = localConfig.cf.get(
                                        repo, 'STATUS_CI_SUCCESS')
                                    logger.info(
                                        "Successful trigger logic for CORRECT failed comment: %s; sha: %s"
                                        % (PR, shortId))
                                    await gh.delete(update_url)
                                    await gh.post(
                                        comment_url,
                                        data={"body": update_message})
                else:
                    await my_create_add_ci_failure_summary(
                        gh, context, comment_url, ci_link, shortId, PR,
                        comment_list, commits_url)


async def my_create_add_ci_failure_summary(
    gh, context, comment_url, ci_link, shortId, PR, comment_list, commits_url):
    """gradually find failed CI"""
    hyperlink_format = '<a href="{link}">{text}</a>'
    failed_header = "## 🕵️ CI failures summary\r\n"
    failed_template = "🔍 PR: <b>#%s</b> Commit ID: <b>%s</b> contains  failed CI.\r\n\r\n"
    failed_ci_bullet = "- <b>Failed: %s</b>"
    failed_ci_hyperlink = hyperlink_format.format(link=ci_link, text=context)
    bot_name = 'just-test-paddle[bot]'

    # 下载日志，返回日志路径
    # FIXME: 返回None不一定代表下载日志失败，也有可能在git-clone阶段就失败不需要下载日志
    log_path = get_failed_log(ci_link)

    # 处理日志，得到describe折叠后的那一行描述，error_log折叠前的日志内容
    describe, error_log = process_failed_log(log_path)

    # 如果当前评论为0，直接新增一个评论就好了
    if len(comment_list) == 0:
        if ci_link.startswith('https://xly.bce.baidu.com'):
            error_message = failed_header + failed_template % (
                str(PR), str(shortId)) + generate_failed_ci_item(
                    ci_link, context, describe, error_log)
            logger.info(
                "Successful trigger logic for CREATE XLY bullet: %s; sha: %s" %
                (PR, shortId))
            await gh.post(comment_url, data={"body": error_message})
            await clean_parent_comment_list(gh, commits_url, PR, shortId)
        else:
            error_message = failed_header + failed_template % (
                str(PR), str(shortId)) + failed_ci_bullet % context
            logger.info(
                "Successful trigger logic for CREATE TC bullet: %s; sha: %s" %
                (PR, shortId))
            await gh.post(comment_url, data={"body": error_message})
            await clean_parent_comment_list(gh, commits_url, PR, shortId)
    else:
        # 遍历评论列表
        for i in range(len(comment_list)):
            comment_sender = comment_list[i]['user']['login']
            comment_body = comment_list[i]['body']
            update_url = comment_list[i]['url']
            # 找到‘我’发送的评论，并且是PR失败的评论
            if comment_sender == bot_name and comment_body.startswith('## 🕵️'):
                # 处理ci_link是效率云平台的事件
                if ci_link.startswith('https://xly.bce.baidu.com'):
                    # 按行分割评论为一个数组
                    # split_body = comment_body.split("\r\n")
                    split_body = re.split(r'[\r\n,\n]', comment_body)
                    # logger.info('after split:', split_body)
                    # 删除当前CI有关的评论
                    split_body = remove_myself(split_body, context)
                    # logger.info('after remove:', split_body)
                    # 重新再当前CI最新的评论加到末尾
                    split_body = append_myself(split_body, ci_link, context,
                                               describe, error_log)
                    # logger.info('after append:', split_body)
                    split_body = add_crlf(split_body)
                    logger.info(
                        "Successful trigger logic for REMOVING and ADDING XLY bullet: %s; sha: %s"
                        % (PR, shortId))
                    # FIXME:TypeError: can only join an iterable
                    update_message = ''.join(split_body)
                    # update_message = my_comment.get_all()
                    await gh.patch(update_url, data={"body": update_message})
                    # FIXME: break?
                    break
                # 还有其它什么事件?
                else:
                    corrected_ci = failed_ci_bullet % context
                    if corrected_ci in split_body:
                        latest_body = comment_body.replace(
                            "\r\n" + corrected_ci, '')
                        update_message = latest_body + "\r\n" + failed_ci_bullet % context
                        logger.info(
                            "Successful trigger logic for ADDING TC bullet: %s; sha: %s"
                            % (PR, shortId))
                        await gh.patch(
                            update_url, data={"body": update_message})
                    else:
                        update_message = comment_body + "\r\n" + failed_ci_bullet % context
                        await gh.patch(
                            update_url, data={"body": update_message})
            # 如果之前评论是通过的
            elif comment_sender == bot_name and comment_body.startswith('✅'):
                if ci_link.startswith('https://xly.bce.baidu.com'):
                    update_message = failed_header + failed_template % (
                        str(PR), str(shortId)) + generate_failed_ci_item(
                            ci_link, context, describe, error_log)
                    logger.info(
                        "Successful trigger logic for CHANGE Success Comment to XLY bullet: %s; sha: %s"
                        % (PR, shortId))
                    await gh.delete(update_url)
                    await gh.post(comment_url, data={"body": update_message})
                else:
                    update_message = failed_header + failed_template % (
                        str(PR), str(shortId)) + generate_failed_ci_item(
                            ci_link, context, error_log)
                    logger.info(
                        "Successful trigger logic for CHANGE Success Comment to TC bullet: %s; sha: %s"
                        % (PR, shortId))
                    await gh.delete(update_url)
                    await gh.post(comment_url, data={"body": update_message})


async def my_update_ci_failure_summary(gh, context, ci_link, comment_list, PR,
                                       shortId):
    """erase corrected CI"""
    failed_ci_bullet = "- <b>Failed: %s</b>"
    # TODO: 记得更改bot-name!!!!!!
    bot_name = "just-test-paddle[bot]"
    for i in range(len(comment_list)):
        comment_sender = comment_list[i]['user']['login']
        comment_body = comment_list[i]['body']
        update_url = comment_list[i]['url']
        if comment_sender == bot_name and comment_body.startswith('## 🕵️'):
            split_body = comment_body.split("\r\n")
            context_list = re.findall(r"\">(.+?)</a></b>", comment_body)
            if ci_link.startswith('https://xly.bce.baidu.com'):
                split_body = comment_body.split("\r\n")
                split_body = remove_myself(split_body, context)
                if have_failed_ci(split_body):
                    logger.info(
                        "Successful trigger logic for ERASE corrected XLY bullet: %s; sha: %s"
                        % (PR, shortId))
                    update_message = ''.join(split_body)
                    await gh.patch(update_url, data={"body": update_message})
                else:
                    logger.info(
                        "ERASE ALL comment as NO bullet left after erase last XLY bullet: %s; sha: %s"
                        % (PR, shortId))
                    await gh.delete(update_url)
            else:
                corrected_ci = failed_ci_bullet % context
                if corrected_ci in split_body:
                    update_message = comment_body.replace(
                        "\r\n" + corrected_ci, '')
                    curr_split_body = update_message.split("\r\n")
                    if len(curr_split_body) > 2:
                        logger.info(
                            "Successful trigger logic for ERASE corrected TC bullet: %s; sha: %s"
                            % (PR, shortId))
                        await gh.patch(
                            update_url, data={"body": update_message})
                    else:
                        logger.info(
                            "ERASE ALL comment as NO bullet left after erase last TC bullet: %s; sha: %s"
                            % (PR, shortId))
                        await gh.delete(update_url)
