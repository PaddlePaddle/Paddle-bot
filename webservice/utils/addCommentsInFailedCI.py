#!/usr/bin/python3
import sys
sys.path.append("..")
sys.path.append(".")
import os
from utils.readConfig import ReadConfig
from utils.auth_ipipe import Get_ipipe_auth
from utils.handler import xlyHandler
from utils.LogProcess import LogProcessMap
import requests
import logging
import re

# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3246472/job/607918://xly.bce.baidu.com/paddlepaddle/Paddle-Bot/newipipe/detail/3222850/job/5980154'
local_config = ReadConfig(path='conf/config.ini')
logging.basicConfig(
    level=logging.INFO,
    filename='./logs/event.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# container
# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3346261/job/6472579'

# sa
# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3346268/job/6472595'
# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3346262/job/6472581'
# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3346257/job/6472572'

target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3389740/job/6647699'

# error_patterns = { 
#                  'abort': 1,
#                  'Your change doesn\'t follow python\'s code style.': 1,
# 		 'make: \*\*\* [all] Error 2' : 1, # excode 7 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2503801/job/3499729
#                  'The following tests FAILED' : 1, # excode 8 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2487781/job/3481353
#                  'There are * approved errors.': 1, # excode 6 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2502654/job/3498271
#                  'Coverage Failed!': 1, # excode 9 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2484394/job/3477511
#                  'Code format error': 1, # excode 4 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2479299/job/3472009
#                  'Merge conflict': 1 # excode 2 https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2616766/job/3649977
# }

# 找不到excode关键字
# https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2503735/job/3499641

# no excode
# check docker md5 fail ! https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2555018/job/3564288

#--------------------------------log and excode related-----------------------------
_EXCODE_DICT = { 'docker_build_failed': 64,\
        'clone_code_failed': 63, \
        'temporary_files_failed': 65,\
        'build_failed': 7,\
        'test_failed': 8,\
        'coverage_failed': 9,\
        'http_proxy_failed': 503,\
        'approve_failed': 6,\
        'code_style_failed': 4,\
        'code_conflict': 2,\
        'code_too_old': 15 }


# FIXME: import from other module
def get_stage_url(target_url):
    pipeline_build_id = target_url.split('/')[-3]
    stage_url = local_config.cf.get('ipipeConf',
                                    'stage_url') + pipeline_build_id
    return stage_url


def download_log(logUrl, job):
    xly = xlyHandler()
    # 下载到logs目录下
    if not os.path.exists('logs'):
        os.mkdir('logs')
    log_name = 'logs/stageBuildId-%d_jobId-%d.log' % (job['stageBuildId'],
                                                      job['id'])
    xly.getJobLog(log_name, logUrl)
    return log_name


def read_log(log_name):
    if not os.path.exists(log_name):
        return None
    # TODO: efficient
    # read last N lines
    # TODO: catch exception
    ret = []
    file = open(log_name, 'r')
    while True:
        line = file.readline()
        if not line:
            break
        ret.append(line)
    file.close()
    os.unlink(log_name)
    return ret


def recv_log_in_mem(logUrl):
    try:
        r = requests.get(logUrl)
    except Exception as e:
        print('Error: %s' % (e))
        logger.warn("Error: %s" % e)
    else:
        return str(r.content, encoding='utf-8')
    return None


def download_and_read_log(logUrl, job):
    log_name = download_log(logUrl, job)
    return read_log(log_name)


def get_container_failed_log(stage_build_beans):
    for stage in stage_build_beans:
        stage_name = stage['stageName']
        job_group_build_beans = stage['jobGroupBuildBeans'][0]
        if stage_name == 'clone code':
            if stage['status'] == 'FAIL':
                # 如果在clone-code阶段就失败了，那么就不下载了
                # print('failed in clone code stage')
                ## TODO: 在PR页面显示这个错误原因
                # return None
                return 'failed in clone code stage'
        else:
            for job in job_group_build_beans:
                job_name = job['jobName']
                status = job['status']
                if job_name in ['build-docker-image', 'Git-clone']:
                    if status == 'FAIL':
                        # 如果在build-docker-image就失败了，那么就不下载了
                        ## TODO: 在PR页面显示是什么错误原因
                        # print('failed in Xxxx job')
                        # return None
                        return 'failed in %s job' % (job_name)
                    continue
                if status == 'FAIL':
                    logParam = job['realJobBuild']['logUrl']
                    logUrl = local_config.cf.get('ipipeConf',
                                                 'log_url') + logParam
                    return recv_log_in_mem(logUrl)
    return None


def get_sa_failed_log(stage_build_beans):
    for stage in stage_build_beans:
        job_group_build_beans = stage['jobGroupBuildBeans'][0]
        for job in job_group_build_beans:
            job_name = job['jobName']
            status = job['status']
            if job_name == 'Git-clone':
                # 如果在Git-cline阶段就失败了，那么就不下载了
                if status == 'FAIL':
                    # print('failed in Git-clone job')
                    ## TODO: 在PR页面显示是什么错误原因
                    return 'failed in GIt-clone job'
            else:
                if status == 'FAIL':
                    taskid = job['realJobBuild']['shellBuild']['taskId']
                    logUrl = "https://xly.bce.baidu.com/paddlepaddle/paddle-ci/sa_log/log/download/%s" % taskid
                    return recv_log_in_mem(logUrl)
    return None


def get_failed_log(target_url):
    stage_url = get_stage_url(target_url)
    session, req = Get_ipipe_auth(stage_url)
    try:
        res = session.send(req).json()
    except Exception as e:
        print('Error: %s' % e)
        log.warn('Error: %s' % (e))
    else:
        paddle_container_ci = tuple(
            local_config.cf.get('CIIndexScope', 'Paddle_container_ci').split(
                ','))
        # 根据pipelineConfName判断是容器类任务还是Sa任务，执行对应的log下载操作
        stage_build_beans = res['pipelineBuildBean']['stageBuildBeans']
        if res['pipelineConfName'].startswith(paddle_container_ci):
            return get_container_failed_log(stage_build_beans)
        return get_sa_failed_log(stage_build_beans)
    return None


def remove_prefix_date(line):
    result = re.match(r"(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})",
                      line)
    if result != None:
        line = line[result.span()[1] + 1:]
    return line


def get_excode(line):
    index = line.find('EXCODE: ')
    if index != -1:
        ret = 0
        for i in range(index + 8, len(line)):
            if line[i] < '0' or line[i] > '9':
                break
            ret = ret * 10 + int(line[i])
        return str(ret) if ret != 0 else '-1'
    if line.find('Failed to connect to') != -1:
        return '503'
    # TODO:

    return '-1'


def get_excode_from_log(log_arr):
    excode = '-1'
    # 每行
    skip_word = ['+ ', '- ', '\n', '\r\n']
    for line in log_arr:
        line = remove_prefix_date(line)
        if len(line) == 0 or (len(line) > 1 and line[0:2] in skip_word):
            continue
        excode = get_excode(line)
        if excode != '-1':
            break
    return excode


def split_str_and_reserve_delimiter(log_str, delimiter):
    return [k + delimiter for k in log_str.split(delimiter)]


# 传入的参数log_str是整个日志内容，类型为string
# FIXME: 如果可以断言要截取的日志一定在最后的N行，那么可以只传入部分日志
# 但是这个N应该怎么确定
def process_failed_log(log_str):
    if log_str == None:
        return 'Unknown Failed', None
    # 在clone code获取build docker步骤失败
    if log_str.startswith('failed in') or len(log_str) < 100:
        return log_str, None
    log_arr = split_str_and_reserve_delimiter(log_str, '\n')
    excode = get_excode_from_log(log_arr)
    dispatcher = LogProcessMap(_EXCODE_DICT)
    return dispatcher.run(excode, log_arr)


# ------------------------CI related-----------------------------


def generate_item_title(pr, shortId):
    failed_header = "## 🕵️ CI failures summary\r\n"
    failed_template = "🔍 PR: <b>#%s</b> Commit ID: <b>%s</b> contains  failed  CI.\r\n"
    return failed_header + failed_template % (str(pr), str(shortId))


def generate_item_header(ci_link, context):
    hyperlink_format = '<a href="{link}">{text}</a>'
    failed_ci_bullet = "<b>Failed: %s</b>"
    failed_ci_hyperlink = hyperlink_format.format(link=ci_link, text=context)
    item = failed_ci_bullet % failed_ci_hyperlink
    return item


def generate_item_tail(describe, error_log):
    log = '<details><summary>%s</summary><pre><code>%s</code></pre></details>\r\n' % (
        describe, error_log if error_log != None else describe)
    return log


def generate_failed_ci_item(ci_link, context, describe, error_log):
    header = generate_item_header(ci_link, context)
    tail = generate_item_tail(describe, error_log) if describe != None else ''
    ret = header + tail
    return ret


def remove_myself(body_arr, ci_name):
    index_arr = find_ci_item_start_and_end_index(body_arr)
    for index in index_arr:
        # 找到当前ci的相关评论删掉它
        if body_arr[index[0]].find(ci_name) != -1:
            body_arr[index[0]:] = body_arr[index[1] + 1:] if index[
                1] >= 0 else []
            # FIXME: 如果两条要交换的评论长度不同怎么办？
            break
    return body_arr


def add_crlf(body_arr):
    for i in range(len(body_arr)):
        if not body_arr[i].endswith('\r\n') or not body_arr[i].endswith('\n'):
            body_arr[i] = body_arr[i] + '\r\n'
    return body_arr


# 找到每条ci的开头第一行的索引，以数组的形式返回
# 例如,Failed: PR-CI-Bot-...
def find_ci_item_start_index(body_arr):
    ret = []
    for i in range(len(body_arr)):
        if re.search(r"\">(.+?)</a></b>", body_arr[i]):
            ret.append(i)
    return ret


# 返回每条ci的开始和结束位置的索引，前闭后闭
# 例如:[1,3]表示当前ci相关评论在索引1到索引3（包含）
# FIXME: return [ start, length ]
def find_ci_item_start_and_end_index(body_arr):
    start_index_arr = find_ci_item_start_index(body_arr)
    ret = []
    for i in range(len(start_index_arr)):
        ret.append([
            start_index_arr[i], start_index_arr[i + 1] - 1
            if i < len(start_index_arr) - 1 else -1
        ])
    return ret


def append_myself(body_arr, ci_name, context, describe, error_log):
    item = generate_failed_ci_item(ci_name, context, describe, error_log)
    body_arr.append(item)
    return body_arr


def have_failed_ci(body_arr):
    for line in body_arr:
        if re.search(r"\">(.+?)</a></b>", line):
            return True
    return False


target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3406023/job/6708016'
log_content = get_failed_log(target_url)
print('log_content[%s]...' % (log_content[0:25]))
describe, content = process_failed_log(log_content)
print('describe=[%s]' % (describe))
print('content=[%s]' % (content))
