#!/usr/bin/python3
import sys
sys.path.append("..")
from utils.readConfig import ReadConfig
from utils.auth_ipipe import Get_ipipe_auth
from utils.handler import xlyHandler
import heapq
import re

# target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/3246472/job/607918://xly.bce.baidu.com/paddlepaddle/Paddle-Bot/newipipe/detail/3222850/job/5980154'
local_config = ReadConfig(path='conf/config.ini')

error_patterns = {
    'abort': 1,
    'Your change doesn\'t follow python\'s code style.': 1
}


# FIXME: import from other module
def get_stage_url(target_url):
    pipeline_build_id = target_url.split('/')[-3]
    stage_url = local_config.cf.get('ipipeConf',
                                    'stage_url') + pipeline_build_id
    return stage_url


# TODO: use memory data base
def get_failed_log(target_url):
    stage_url = get_stage_url(target_url)

    session, req = Get_ipipe_auth(stage_url)
    try:
        res = session.send(req).json()
    except Exception as e:
        print('Error: %s' % e)
    else:
        stage_build_beans = res['pipelineBuildBean']['stageBuildBeans']
        print(stage_build_beans)
        xly = xlyHandler()
        for stage in stage_build_beans:
            if stage['stageName'] in ['clone code']:
                continue
            job_group_build_beans = stage['jobGroupBuildBeans'][0]
            for job in job_group_build_beans:
                if job['jobName'] in ['build-docker-image']:
                    continue
                job_name = job['jobName']
                status = job['status']
                if status == 'FAIL':
                    # FIXME: Sa or other
                    if 'logUrl' in job['realJobBuild']:
                        logParam = job['realJobBuild']['logUrl']
                        logUrl = local_config.cf.get('ipipeConf',
                                                     'log_url') + logParam
                    else:
                        taskId = job['realJobBuild']['shellBuild']['taskId']
                        logUrl = 'https://xly.bce.baidu.com/paddlepaddle/paddle-ci/sa_log/log/download/%s' % taskId
                    log_name = 'stageBuildId-%d_jobId-%d_jobName-%s.log' % (
                        job['stageBuildId'], job['id'], job['jobName'])
                    xly.getJobLog(log_name, logUrl)
                    return log_name
    return None


class Entry:
    def __init__(self, index, priority):
        self.index = index
        self.priority = priority

    def __cmp__(self, other):
        if self.priority < other.priority:
            return -1
        if self.priority > other.priority:
            return 1
        if self.index < other.index:
            return -1
        if self.index > other.index:
            return 1
        return 0

    # FIXME:
    def __lt__(self, other):
        if self.priority < other.priority:
            return -1
        if self.priority > other.priority:
            return 1
        if self.index < other.index:
            return -1
        if self.index > other.index:
            return 1
        return 0


def remove_prefix_date(line):
    result = re.match(r"(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})",
                      line)
    if result != None:
        line = line[result.span()[1] + 1:]
    return line


def process_failed_log(failed_log_path):
    content = []
    q = []
    index = 0
    bias = 10
    skip_word = ['+ ', '- ']
    with open(failed_log_path, 'rt') as fd:
        for line in fd:
            line = remove_prefix_date(line)
            # line = skip_redundant_line( line )
            # print( '[%s]' % ( line ) )
            if len(line) > 1 and line[0:2] in skip_word:
                continue
            content.append(line)
            for pattern, priority in error_patterns.items():
                if re.search(pattern, line):
                    entry = Entry(index, priority)
                    heapq.heappush(q, entry)
            index += 1
    fd.close()
    # TODO: remove log in file system
    if len(q) == 0:
        return None, None
    entry = heapq.heappop(q)
    # [ 0, n) 
    left = max(0, entry.index - bias)
    right = min(len(content), entry.index + bias + 1)
    ret = content[left:right]
    ret = ''.join(ret)
    return content[entry.index], ret


def generate_item_header(ci_link, context):
    hyperlink_format = '<a href="{link}">{text}</a>'
    failed_ci_bullet = "<b>Failed: %s</b>\r\n"
    failed_ci_hyperlink = hyperlink_format.format(link=ci_link, text=context)
    item = failed_ci_bullet % failed_ci_hyperlink
    return item


def generate_item_tail(describe, error_log):
    log = '%s<pre><code>%s</code></pre>\r\n' % (describe, error_log)
    return log


def generate_failed_ci_item(ci_link, context, describe, error_log):
    header = generate_item_header(ci_link, context)
    tail = generate_item_tail(describe, error_log)
    return header + tail


def remove_myself(body_arr, ci_name):
    if len(body_arr) == 0:
        return
    left = -1
    for i in range(len(body_arr)):
        if body_arr[i].find(ci_name) != -1:
            left = i
            break
    if left == -1:
        return body_arr
    right = left + 1
    for i in range(right, len(body_arr)):
        # FIXME: use reg exp
        if body_arr[i].find('PR'):
            break
        right += 1
    right = min(right, len(body_arr) - 1)
    body_arr[left, right] = body_arr[right:]
    return body_arr


def append_myself(body_arr, ci_name, context, describe, error_log):
    item = generate_failed_ci_item(ci_name, context, describe, error_log)
    body_arr.append(item)


def have_failed_ci(body_arr):
    for line in body_arr:
        # FIXME: use reg exp
        if line.find('Failed:'):
            return True
    return False


# log_name = get_failed_log( target_url )
# assert log_name != None
# describe, error_log = process_failed_log( log_name )
# 
# print( 'error_log =', error_log )
# 
# ci_item = generate_failed_ci_item( target_url, 'PR-CI-Bot-CheckCodeStyle', describe, error_log )
# print( ci_item )
