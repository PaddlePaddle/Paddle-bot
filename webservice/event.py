from gidgethub import routing
from utils.check import checkPRNotCI, checkPRTemplate, checkComments, checkCIState, checkRequired, getPRNum, getCommitComments, ifCancelXly, xlyJob
from utils.readConfig import ReadConfig
from utils.analyze_buildLog import ifDocumentFix, ifAlreadyExist, analysisBuildLog  #getBasicCIIndex, getDetailsCIIndex
from utils.db import Database
from utils.convert import javaTimeTotimeStamp
from utils.addCommentsInFailedCI import get_failed_log, process_failed_log, generate_failed_ci_item, remove_myself, append_myself, have_failed_ci, split_str_and_reserve_delimiter
import time
import logging
from logging import handlers
import re
import json
import requests
import datetime
import os
router = routing.Router()
localConfig = ReadConfig()

logger = logging.getLogger(__name__)

log_file = "./logs/event.log"
fh = handlers.RotatingFileHandler(
    filename=log_file, maxBytes=1500000000, backupCount=10, encoding="utf-8")
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)


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
    pr_open_auto_reply_repos = localConfig.cf.get('FunctionScope',
                                                  'PR_open_auto_reply')
    if repo not in pr_open_auto_reply_repos:
        repo = 'Others'
    if base_branch.startswith(
            'PaddlePaddle:release') and repo == 'PaddlePaddle/Paddle':
        message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED')
        logger.info("%s_%s Trigger CI Successful." % (pr_num, sha))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})
    else:
        if checkPRNotCI(commit_url, sha) == False:
            if repo == 'PaddlePaddle/docs':
                preview_url = 'http://preview-pr-%s.paddle-docs-preview.paddlepaddle.org.cn/documentation/docs/zh/api/index_cn.html' % pr_num
                wiki_url = "https://github.com/PaddlePaddle/docs/wiki/%5BBeta%5D%E9%A3%9E%E6%A1%A8%E6%96%87%E6%A1%A3%E9%A2%84%E8%A7%88%E5%B7%A5%E5%85%B7"
                message = "感谢你贡献飞桨文档，文档预览构建中，Docs-New 跑完后即可预览，预览链接：%s \n" % preview_url
                message += "预览工具的更多说明，请参考：[[Beta]飞桨文档预览工具](%s)" % wiki_url
            else:
                message = localConfig.cf.get(repo, 'PULL_REQUEST_OPENED')
            logger.info("%s_%s Trigger CI Successful %s" %
                        (pr_num, sha, message))
        else:
            message = "Hi, It's a test PR, it will not trigger CI. If you want to trigger CI, please remove `notest` in your commit message."
            logger.info("%s_%s is a test PR." % (pr_num, sha))
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})


#给PR打label, 目前只打外部开发者的
@router.register("pull_request", action="opened")
@router.register("pull_request", action="closed")
async def pull_request_label_for_external(event, gh, repo, *args, **kwargs):
    """Check if PR triggers CI"""
    PR_label_for_external_repos = localConfig.cf.get('FunctionScope',
                                                     'PR_label_for_external')
    if repo not in PR_label_for_external_repos:
        return
    today = datetime.date.today()
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    commit_url = event.data["pull_request"]["commits_url"]
    sha = event.data["pull_request"]["head"]["sha"]
    base_branch = event.data["pull_request"]['base']['label']
    user = event.data["sender"]['login']
    label_url = 'https://api.github.com/repos/%s/issues/%s/labels' % (repo,
                                                                      pr_num)
    f = open("buildLog/person_on_job-%s.log" % today)
    person_on_job = f.read()
    if user not in person_on_job:
        if event.data['action'] == 'opened':
            logger.info("%s_%s create PR Successful." % (user, pr_num))
            create_labels = ['contributor', 'status: proposed']
            await gh.post(label_url, data={"labels": create_labels})
        elif event.data['action'] == 'closed':
            pr_labels = event.data['pull_request']['labels']
            delete_label_name_list = []
            for label_id in pr_labels:
                name = label_id['name']
                if name.startswith('status'):
                    delete_label_name_list.append(name)
            if len(delete_label_name_list) != 0:
                for delete_label_name in delete_label_name_list:
                    logger.info(
                        "%s_%s remove last status label(%s) successful!" %
                        (user, pr_num, delete_label_name))
                    label_delete_url = 'https://api.github.com/repos/%s/issues/%s/labels/%s' % (
                        repo, pr_num, delete_label_name)
                    await gh.delete(label_delete_url)
            ifMerge = event.data["pull_request"]['merged']
            logger.info("%s_%s merged: %s." % (user, pr_num, ifMerge))
            if ifMerge == False:
                close_label = ['status: not progressed']
                await gh.post(label_url, data={"labels": close_label})
            else:
                close_label = ['status: accepted']
                await gh.post(label_url, data={"labels": close_label})
    f.close()


@router.register("pull_request", action="labeled")
async def pull_request_label_send_message(event, gh, repo, *args, **kwargs):
    pr_num = event.data['number']
    user = event.data["sender"]['login']
    label = event.data['label']['name']
    if label in ['status: proposed', 'contributor']:
        return
    PR_label_for_external_repos = localConfig.cf.get('FunctionScope',
                                                     'PR_label_for_external')
    if repo not in PR_label_for_external_repos:
        return
    pr_labels = event.data['pull_request']['labels']
    delete_label_name_list = []
    for label_id in pr_labels:
        name = label_id['name']
        logger.info('pr_labels name: %s' % name)
        if name.startswith(
                'status') and name != label and label != 'contributor':
            delete_label_name_list.append(name)
    if len(delete_label_name_list) != 0:
        for delete_label_name in delete_label_name_list:
            logger.info("%s_%s remove last status label(%s) successful!" %
                        (user, pr_num, delete_label_name))
            label_delete_url = 'https://api.github.com/repos/%s/issues/%s/labels/%s' % (
                repo, pr_num, delete_label_name)
            await gh.delete(label_delete_url)
    if label == 'status: open review':
        message = localConfig.cf.get(repo, 'PR_LABEL_OPEN_REVIEW')
    elif label == 'status: revision':
        message = localConfig.cf.get(repo, 'PR_LABEL_REVISION')
    elif label == 'status: accepted':
        message = localConfig.cf.get(repo, 'PR_LABEL_ACCEPT')
    elif label == 'status: not progressed':
        message = localConfig.cf.get(repo, 'PR_LABEL_NOT_PROGRESSED')
    elif label == 'status: testing':
        message = localConfig.cf.get(repo, 'PR_LABEL_TESTING')
    elif label == 'status: finished':
        message = localConfig.cf.get(repo, 'PR_LABEL_FINISHED')
    else:
        message = ''
    if message != '':
        url = event.data["pull_request"]["comments_url"]
        logger.info("%s add label %s successful!" % (pr_num, label))
        await gh.post(url, data={"body": message})


@router.register("issues", action="labeled")
async def issue_label_for_icafe(event, gh, repo, *args, **kwargs):
    PR_label_for_external_repos = localConfig.cf.get('FunctionScope',
                                                     'PR_label_for_external')
    if repo not in PR_label_for_external_repos:
        return
    issue_num = event.data['issue']['number']
    cur_label = event.data['label']['name']
    issue_status = event.data['issue']['state']
    if cur_label in ['status/close', 'status/developed']:
        data = {"state": "closed"}
        url = "https://api.github.com/repos/%s/issues/%s" % (repo, issue_num)
        await gh.patch(url, data=data)
        logger.info("issues: %s closed success!" % issue_num)
    if issue_status == 'closed' and cur_label not in [
            'status/developed', 'status/close'
    ] and cur_label.startswith('status/'):
        data = {"state": "open"}
        url = "https://api.github.com/repos/%s/issues/%s" % (repo, issue_num)
        logger.info("issues url: %s" % url)
        await gh.patch(url, data=data)
        logger.info("issues: %s reopen success!" % issue_num)

    if cur_label.startswith('type/'):
        remove_label = 'type/'
    elif cur_label.startswith('status/'):
        remove_label = 'status/'
    else:
        remove_label = ''
    if remove_label != '':
        old_labels = event.data['issue']['labels']
        for l in old_labels:
            if l['name'].startswith(remove_label) and l['name'] != cur_label:
                label_delete_url = 'https://api.github.com/repos/%s/issues/%s/labels/%s' % (
                    repo, issue_num, l['name'])
                await gh.delete(label_delete_url)
                logger.info("%s remove last status label(%s) successful!" %
                            (issue_num, l['name']))


@router.register("pull_request", action="edited")
@router.register("pull_request", action="synchronize")
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
                            "paddle-bot-test[bot]", "just-test-paddle[bot]"
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
                        "paddle-bot-test[bot]", "just-test-paddle[bot]"
                ] and comment_body.startswith('❌ The PR'):
                    message = localConfig.cf.get(repo,
                                                 'PR_CORRECT_DESCRIPTION')
                    logger.info("%s Correct PR Description and Meet Template" %
                                pr_num)
                    update_url = comment_list[i]['url']
                    await gh.patch(update_url, data={"body": message})


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


@router.register("check_run", action="created")
async def running_check_run(event, gh, repo, *args, **kwargs):
    """running checkrun"""
    url = event.data["check_run"]["url"]
    name = event.data["check_run"]["name"]
    #data = {"name": name, "status": "in_progress"}
    #await gh.patch(url, data=data, accept='application/vnd.github.antiope-preview+json') 
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
    if sender == 'paddle-bot-test[bot]':
        message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
        await gh.post(url, data={"body": message})


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
        # que_msg = "%s\r\n%s" % (localConfig.cf.get(repo, 'ISSUE_OPENED_QUE'), localConfig.cf.get(repo, 'QUE_LINK'))
        logger.info("%s Issue %s automatic reply successfully." %
                    (repo, issue_num))
        await gh.post(url, data={"body": message})
        # time.sleep(0.1)
        # await gh.post(url, data={"body": que_msg})


@router.register("issues", action="closed")
async def check_close_regularly(event, gh, repo, *args, **kwargs):
    """check_close_regularly"""
    issue_num = event.data["issue"]["number"]
    issue_effect_repos = localConfig.cf.get('FunctionScope',
                                            'ISSUE_close_auto_reply')
    if repo in issue_effect_repos:
        url = event.data["issue"]["comments_url"]
        sender = event.data["sender"]["login"]
        if sender == 'paddle-bot-test[bot]':
            old_labels = event.data['issue']['labels']
            is_icafe_closed = False
            for l in old_labels:
                if l['name'] in ['status/close', 'status/developed']:
                    is_icafe_closed = True
            if is_icafe_closed == False:
                message = localConfig.cf.get(repo, 'CLOSE_REGULAR')
                await gh.post(url, data={"body": message})
        else:
            label_github = ['status/close']
            label_url = 'https://api.github.com/repos/%s/issues/%s/labels' % (
                repo, issue_num)
            logger.info("label_url: %s" % label_url)
            await gh.post(label_url, data={"labels": label_github})
            logger.info("%s closed success, and label" % issue_num)


#Issue reopen自动打标签: ISSUE_reopen_auto_label
@router.register("issues", action="reopened")
async def ISSUE_reopen_auto_label(event, gh, repo, *args, **kwargs):
    """Automatically respond to users"""
    issue_effect_repos = localConfig.cf.get('FunctionScope',
                                            'ISSUE_open_auto_reply')
    if repo in issue_effect_repos:
        issue_num = event.data['issue']['number']
        sender = event.data["sender"]["login"]
        if sender != 'paddle-bot-test[bot]':
            label_github = ['status/reopen']
            label_url = 'https://api.github.com/repos/%s/issues/%s/labels' % (
                repo, issue_num)
            logger.info("label_url: %s" % label_url)
            await gh.post(label_url, data={"labels": label_github})
            logger.info("%s reopen success, and label" % issue_num)
