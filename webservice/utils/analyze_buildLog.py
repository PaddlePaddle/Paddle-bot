#coding=utf-8
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from utils.readConfig import ReadConfig
from utils.auth_ipipe import Get_ipipe_auth
from utils.db import Database
from utils import bosclient
from utils.mail import Mail
import pandas as pd
import os
import time
import datetime
import logging
import wlist_alarm
from tornado.httpclient import AsyncHTTPClient
import json

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
localConfig = ReadConfig()

logging.basicConfig(
    level=logging.INFO,
    filename='./logs/event.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def ifDocumentFix(message):
    document_fix = True if 'test=document_fix' in message else False
    return document_fix


def ifAlreadyExist(query_stat):
    db = Database()
    result = list(db.query(query_stat))
    queryTime = ''
    if len(result) != 0:
        queryTime = result[0][0]['time'].split('.')[0].replace('T', ' ')
        queryTime = time.strptime(queryTime, '%Y-%m-%d %H:%M:%S')
        dt = datetime.datetime.fromtimestamp(time.mktime(queryTime))
        actualQueryTime = (
            dt + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        timeArray = time.strptime(actualQueryTime, "%Y-%m-%d %H:%M:%S")
        queryTime = int(time.mktime(timeArray))
    return queryTime


def get_stageUrl(target_url):
    pipelineBuildid = target_url.split('/')[-3]
    stage_url = localConfig.cf.get('ipipeConf', 'stage_url') + pipelineBuildid
    return stage_url


def getBasicCIIndex(repo, sha, document_fix, target_url):
    """
    获取CI基础指标: 时间 + 状态 + 退出码
    1. 退出码的获取需要分析日志
    """
    basic_ci_index_dict = {}
    stage_url = get_stageUrl(target_url)
    session, req = Get_ipipe_auth(stage_url)
    try:
        res = session.send(req).json()
        print(session.send(req).text)
    except Exception as e:
        print("Error: %s" % e)
    else:
        try:
            branch = res['branch']
            basic_ci_index_dict['branch'] = branch
            jobGroupBuildBeans = res['pipelineBuildBean']['stageBuildBeans'][
                0]['jobGroupBuildBeans'][0]
            PR = res['pipelineBuildBean']['stageBuildBeans'][0]['outParams'][
                'AGILE_PULL_ID']
            basic_ci_index_dict['PR'] = PR
            commit_createTime = int(
                str(res['pipelineBuildBean']['stageBuildBeans'][0][
                    'startTime'])[:-3])  #commit提交时间/rerun时间
            basic_ci_index_dict['commit_createTime'] = commit_createTime
            docker_build_status = 'SUCC'  #默认认为构建镜像阶段是成功的
            for job in jobGroupBuildBeans:
                jobName = job['jobName']
                if jobName in ['构建镜像', 'build-docker-image']:
                    docker_build_status = job['status']
                    docker_build_startTime = int(
                        str(job['realJobBuild']['startTime'])
                        [:-3])  #docker构建开始时间
                    docker_build_endTime = int(
                        str(job['realJobBuild']['endTime'])[:
                                                            -3])  #docker构建结束时间
                    basic_ci_index_dict[
                        'docker_build_startTime'] = docker_build_startTime
                    basic_ci_index_dict[
                        'docker_build_endTime'] = docker_build_endTime
                    if docker_build_status == 'FAIL':
                        logParam = job['realJobBuild']['logUrl']
                        logUrl = localConfig.cf.get('ipipeConf',
                                                    'log_url') + logParam
                        break
                else:
                    Paddle_sa_ci_tuple = tuple(
                        localConfig.cf.get('CIIndexScope', 'Paddle_sa_ci')
                        .split(','))
                    Other_sa_ci_tuple = tuple(
                        localConfig.cf.get('CIIndexScope', 'Other_sa_ci')
                        .split(','))
                    Paddle_sa_detailed_ci_tuple = tuple(
                        localConfig.cf.get('CIIndexScope',
                                           'Paddle_sa_detailed_ci').split(','))
                    if res['pipelineConfName'].startswith(
                            Paddle_sa_ci_tuple) or res[
                                'pipelineConfName'].startswith(
                                    Other_sa_ci_tuple) or repo in [
                                        'PaddlePaddle/Paddle-Lite',
                                        'PaddlePaddle/models',
                                        'PaddlePaddle/book'
                                    ]:  #sa任务
                        paddle_build_startTime = int(
                            str(job['realJobBuild']['shellBuild']['startTime'])
                            [:-3])  #任务开始时间
                        paddle_build_endTime = int(
                            str(job['realJobBuild']['shellBuild']['endTime'])
                            [:-3])  #任务结束时间
                        if res['pipelineConfName'].startswith(
                                Paddle_sa_detailed_ci_tuple):
                            if document_fix == 'True':
                                EXCODE = 0 if job['status'] == 'SUCC' else 1
                                basic_ci_index_dict['EXCODE'] = EXCODE
                                logUrl = None
                            else:
                                taskid = job['realJobBuild']['shellBuild'][
                                    'taskId']
                                logUrl = "https://xly.bce.baidu.com/paddlepaddle/paddle-ci/sa_log/log/download/%s" % taskid
                        else:
                            EXCODE = 0 if job['status'] == 'SUCC' else 1
                            basic_ci_index_dict['EXCODE'] = EXCODE
                            logUrl = None
                    else:
                        paddle_build_startTime = int(
                            str(job['realJobBuild']['startTime'])
                            [:-3])  #paddle编译开始时间
                        paddle_build_endTime = int(
                            str(job['realJobBuild']['endTime'])
                            [:-3])  #paddle结束开始时间
                        if document_fix == 'True' and not res[
                                'pipelineConfName'].startswith(
                                    'PR-CI-CPU-Py2'):
                            EXCODE = 0 if job['status'] == 'SUCC' else 1
                            basic_ci_index_dict['EXCODE'] = EXCODE
                            logUrl = None
                        else:
                            logParam = job['realJobBuild']['logUrl']
                            logUrl = localConfig.cf.get('ipipeConf',
                                                        'log_url') + logParam
                    if document_fix == 'True':
                        logger.info("%s, document_fix: %s; EXCODE: %s" % (
                            res['pipelineConfName'], document_fix, EXCODE))
                    basic_ci_index_dict[
                        'paddle_build_startTime'] = paddle_build_startTime
                    basic_ci_index_dict[
                        'paddle_build_endTime'] = paddle_build_endTime
        except ValueError:
            print("get TIME ERROR: %s" % target_url)
            logger.error("get TIME ERROR: %s" % target_url)
            basic_ci_index_dict = {}
        else:
            if docker_build_status == 'FAIL':  #构建镜像失败的情况
                docker_build_waitTime = docker_build_startTime - commit_createTime
                docker_build_execTime = docker_build_endTime - docker_build_startTime
                waitTime_total = docker_build_waitTime
                execTime_total = docker_build_execTime
            elif res['pipelineConfName'].startswith(Paddle_sa_ci_tuple) or res[
                    'pipelineConfName'].startswith(
                        Other_sa_ci_tuple) or repo in [
                            'PaddlePaddle/Paddle-Lite', 'PaddlePaddle/models',
                            'PaddlePaddle/book'
                        ]:  #sa任务的时间统计
                waitTime_total = paddle_build_startTime - commit_createTime
                execTime_total = paddle_build_endTime - paddle_build_startTime
            else:
                docker_build_waitTime = docker_build_startTime - commit_createTime
                docker_build_execTime = docker_build_endTime - docker_build_startTime
                paddle_build_waitTime = paddle_build_startTime - docker_build_endTime
                paddle_build_execTime = paddle_build_endTime - paddle_build_startTime
                waitTime_total = paddle_build_waitTime + docker_build_waitTime
                execTime_total = paddle_build_execTime + docker_build_execTime
            basic_ci_index_dict['waitTime_total'] = waitTime_total  #排队总时间
            basic_ci_index_dict['execTime_total'] = execTime_total  #执行总时间
            if logUrl != None:
                getIpipeBuildLog(sha, res['pipelineConfName'],
                                 commit_createTime, logUrl)
                EXCODE = getExcode(sha, res['pipelineConfName'],
                                   commit_createTime)
                basic_ci_index_dict['EXCODE'] = EXCODE
    return basic_ci_index_dict


def getDetailsCIIndex(basic_ci_index, target_url):
    """
    获取CI详细指标: 编译时间/单测时间等等
    1. 日志已经存到本机的前提
    """
    detailed_ci_index_dict = {}
    ciName = basic_ci_index['ciName']
    commitId = basic_ci_index['commitId']
    EXCODE = basic_ci_index['EXCODE']
    detailed_ci_index_dict['ciName'] = ciName
    detailed_ci_index_dict['commitId'] = commitId
    detailed_ci_index_dict['EXCODE'] = EXCODE
    detailed_ci_index_dict['PR'] = int(basic_ci_index['PR'])
    detailed_ci_index_dict['createTime'] = basic_ci_index['commit_createTime']
    detailed_ci_index_dict['branch'] = basic_ci_index['branch']
    detailed_ci_index_dict['repo'] = basic_ci_index['repo']
    detailed_ci_index_dict['endTime'] = basic_ci_index[
        'paddle_build_endTime'] if 'paddle_build_endTime' in basic_ci_index else basic_ci_index[
            'docker_build_endTime']
    detailed_ci_index_dict['documentfix'] = basic_ci_index['documentfix']

    filename = '%s_%s_%s.log' % (ciName, commitId,
                                 basic_ci_index['commit_createTime'])
    f = open('buildLog/%s' % filename, 'r')
    data = f.read()
    analyze_failed_cause(detailed_ci_index_dict, target_url)  #分析PR失败原因
    if ciName.startswith(
        ('PR-CI-APPROVAL',
         'PR-CI-OP-benchmark')) or EXCODE == 7 or EXCODE == 2 or EXCODE == 1:
        pass
    else:
        try:
            buildTime_strlist = data.split('Build Time:', 1)
            buildTime = buildTime_strlist[1:][0].split('s')[0].strip()
            detailed_ci_index_dict['buildTime'] = float(buildTime)
            #收集ccache
            if ciName in [
                    'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-CPU-Py2',
                    'PR-CI-Inference', 'PR-CI-Mac', 'PR-CI-Mac-Python3'
            ]:
                ccacheRate_strlist = data.split('ccache hit rate:', 1)
                ccacheRate = ccacheRate_strlist[1:][0].split('%')[0].strip()
                detailed_ci_index_dict['ccacheRate'] = float(ccacheRate)
            if filename.startswith('PR-CI-Inference'):
                fluidInferenceSize_strlist = data.split(
                    'Paddle_Inference Size:', 1)
                fluidInferenceSize = fluidInferenceSize_strlist[1:][0].split(
                    'M')[0].strip()
                detailed_ci_index_dict['fluidInferenceSize'] = float(
                    fluidInferenceSize)
                testFluidLibTime_strlist = data.split(
                    'test_fluid_lib Total Time:', 1)
                testFluidLibTime = testFluidLibTime_strlist[1:][0].split('s')[
                    0].strip()
                detailed_ci_index_dict['testFluidLibTime'] = float(
                    testFluidLibTime)
                #testFluidLibTrainTime_strlist = data.split('test_fluid_lib_train Total Time:', 1)
                #testFluidLibTrainTime = testFluidLibTrainTime_strlist[1:][0].split('s')[0].strip()
                #index_dict['testFluidLibTrainTime'] = float(testFluidLibTrainTime)
            elif filename.startswith('PR-CI-Coverage') or filename.startswith(
                    'PR-CI-Py3') or filename.startswith('PR-CI-CPU-Py2'):
                buildSize_strlist = data.split('Build Size:', 1)
                buildSize = buildSize_strlist[1:][0].split('G')[0].strip()
                detailed_ci_index_dict['buildSize'] = float(buildSize)
                WhlSize_strlist = data.split('PR whl Size:', 1)
                if filename.startswith('PR-CI-Coverage'):
                    if 'G' in WhlSize_strlist[1:][0].split('\n')[0]:
                        WhlSize = WhlSize_strlist[1:][0].split('G')[0].strip()
                        WhlSize = float(WhlSize) * 1024
                    else:
                        WhlSize = WhlSize_strlist[1:][0].split('M')[0].strip()
                else:
                    WhlSize = WhlSize_strlist[1:][0].split('M')[0].strip()
                detailed_ci_index_dict['WhlSize'] = float(WhlSize)
                if filename.startswith(
                        'PR-CI-Coverage') or filename.startswith('PR-CI-Py3'):
                    if 'Added UT should not exceed 15 seconds' in data:
                        print('Added UT exceed 15 seconds: %s' % target_url)
                        return detailed_ci_index_dict
                    if 'in PRECISION_TEST' in data:  #命中精致测试 只拿testCaseTime_total
                        detailed_ci_index_dict['PRECISION_TEST'] = True
                        testCaseTime_total_strlist = data.split(
                            'TestCases Total Time:')
                        testCaseTime_total = 0
                        if detailed_ci_index_dict['EXCODE'] == 8:
                            for item in testCaseTime_total_strlist[1:]:
                                testCaseTime_total += int(
                                    item.split('s')[0].strip())
                        else:
                            for item in testCaseTime_total_strlist[1:]:
                                testCaseTime_total = int(
                                    item.split('s')[0].strip()
                                ) if int(item.split('s')[0].strip(
                                )) > testCaseTime_total else testCaseTime_total
                        detailed_ci_index_dict[
                            'testCaseTime_total'] = testCaseTime_total
                    else:
                        detailed_ci_index_dict['PRECISION_TEST'] = False
                        testCaseCount_single_strlist = data.split(
                            '1 card TestCases count is')
                        testCaseCount_single = 0
                        for item in testCaseCount_single_strlist[
                                1:]:  #原因是单卡的case分了两部分
                            testCaseCount_single += int(
                                item.split('\n')[0].strip())
                        detailed_ci_index_dict[
                            'testCaseCount_single'] = testCaseCount_single
                        testCaseCount_multi_strlist = data.split(
                            '2 card TestCases count is')
                        testCaseCount_multi = int(testCaseCount_multi_strlist[
                            1:][0].split('\n')[0].strip())
                        detailed_ci_index_dict[
                            'testCaseCount_multi'] = testCaseCount_multi
                        testCaseCount_exclusive_strlist = data.split(
                            'exclusive TestCases count is')
                        testCaseCount_exclusive = int(
                            testCaseCount_exclusive_strlist[1:][0].split('\n')[
                                0].strip())
                        detailed_ci_index_dict[
                            'testCaseCount_exclusive'] = testCaseCount_exclusive
                        testCaseCount_total = testCaseCount_single + testCaseCount_multi + testCaseCount_exclusive
                        detailed_ci_index_dict[
                            'testCaseCount_total'] = testCaseCount_total
                        testCaseTime_single_strlist = data.split(
                            '1 card TestCases Total Time:')
                        testCaseTime_single = 0
                        for item in testCaseTime_single_strlist[
                                1:]:  #原因是单卡的case分了两部分
                            testCaseTime_single += int(
                                item.split('s')[0].strip())
                        detailed_ci_index_dict[
                            'testCaseTime_single'] = testCaseTime_single
                        testCaseTime_multi_strlist = data.split(
                            '2 card TestCases Total Time:')
                        testCaseTime_multi = int(testCaseTime_multi_strlist[1:]
                                                 [0].split('s')[0].strip())
                        detailed_ci_index_dict[
                            'testCaseTime_multi'] = testCaseTime_multi
                        testCaseTime_exclusive_strlist = data.split(
                            'exclusive TestCases Total Time:')
                        testCaseTime_exclusive = int(
                            testCaseTime_exclusive_strlist[1:][0].split('s')[
                                0].strip())
                        detailed_ci_index_dict[
                            'testCaseTime_exclusive'] = testCaseTime_exclusive
                        if detailed_ci_index_dict['EXCODE'] == 8:
                            testCaseTime_total = detailed_ci_index_dict[
                                'testCaseTime_single'] + detailed_ci_index_dict[
                                    'testCaseTime_multi'] + detailed_ci_index_dict[
                                        'testCaseTime_exclusive']
                        else:
                            testCaseTime_total_strlist = data.split(
                                'TestCases Total Time:')
                            testCaseTime_total = 0
                            for item in testCaseTime_total_strlist[1:]:
                                testCaseTime_total = int(
                                    item.split('s')[0].strip()
                                ) if int(item.split('s')[0].strip(
                                )) > testCaseTime_total else testCaseTime_total
                        detailed_ci_index_dict[
                            'testCaseTime_total'] = testCaseTime_total

            elif filename.startswith('PR-CI-Mac'):
                testCaseTime_mac_strlist = data.split('Mac testCase Time:')
                testCaseTime_mac = int(testCaseTime_mac_strlist[1:][0].split(
                    's')[0].strip())
                detailed_ci_index_dict['testCaseTime_total'] = testCaseTime_mac
            elif filename.startswith('PR-CI-Windows'):
                fluidInferenceSize_strlist = data.split(
                    'Windows Paddle_Inference Size:', 1)
                fluidInferenceSize = fluidInferenceSize_strlist[1].split('M')[
                    0].strip()
                detailed_ci_index_dict['fluidInferenceSize'] = float(
                    fluidInferenceSize)
                WhlSize_strlist = data.split('PR whl Size:', 1)
                WhlSize = WhlSize_strlist[1].split('M')[0].strip()
                detailed_ci_index_dict['WhlSize'] = float(WhlSize)
                testCaseTime_single_strlist = data.split(
                    'Windows 1 card TestCases Total Time:')
                testCaseTime_single = int(testCaseTime_single_strlist[1:][0]
                                          .split('s')[0].strip())
                detailed_ci_index_dict[
                    'testCaseTime_single'] = testCaseTime_single
                testCaseTime_win_strlist = data.split(
                    'Windows TestCases Total Time:')
                testCaseTime_win = int(testCaseTime_win_strlist[1:][0].split(
                    's')[0].strip())
                detailed_ci_index_dict['testCaseTime_total'] = testCaseTime_win
                if ciName in ['PR-CI-Windows', 'PR-CI-Windows-OPENBLAS']:
                    buildCache_strlist = data.split(
                        'ipipe_log_param_Windows_Build_Cache: ', 2)
                    buildCache = 1 if buildCache_strlist[1:][0].split('\n')[
                        0].strip() == 'TRUE' else 0
                    detailed_ci_index_dict['buildCache'] = int(buildCache)
                print(detailed_ci_index_dict)
                '''
                testCaseCount_single_strlist = data.split('Windows 1 card TestCases count is')
                testCaseCount_single = int(testCaseCount_single_strlist[-1].split('\n')[0].strip())
                detailed_ci_index_dict['testCaseCount_single'] = testCaseCount_single
                testCaseCount_total = testCaseCount_single
                detailed_ci_index_dict['testCaseCount_total'] = testCaseCount_total
                '''
        except IndexError:
            print('details index get failed: %s' % target_url)
    f.close()

    return detailed_ci_index_dic


def getExcode(sha, pipelineConfName):
    """获取退出码"""
    filename = '%s_%s.log' % (pipelineConfName, sha)
    f = open('buildLog/%s' % filename, 'r')
    data = f.read()
    try:
        if '自动合并失败，修正冲突然后提交修正的结果。' in data or 'Automatic merge failed; fix conflicts and then commit the result.' in data:
            EXCODE = 2
        elif 'Received HTTP code 503 from proxy after CONNECT' in data:
            EXCODE = 503
        elif pipelineConfName.startswith(
                'PR-CI-APPROVAL') or pipelineConfName.startswith('PR-CI-Mac'):
            exitCode_strlist = data.split("EXCODE=", 1)
            EXCODE = int(exitCode_strlist[1:][0][0])
        elif pipelineConfName.startswith('PR-CI-Windows'):
            exitCode_strlist = data.split("EXCODE: ", 1)
            EXCODE = int(exitCode_strlist[1][0].strip())
        else:
            exitCode_strlist = data.split("{build code state=", 1)
            EXCODE = int(exitCode_strlist[1:][0].split('}')[0].strip())
    except IndexError:
        print('get EXCODE failed!!')
        EXCODE = 1
    f.close()
    logger.info("%s_%s EXCODE = %s" % (pipelineConfName, sha, EXCODE))
    return EXCODE


def getIpipeBuildLog(sha, pipelineConfName, logUrl):
    try:
        r = requests.get(logUrl)
    except Exception as e:
        print("Error: %s" % e)
    else:
        with open("buildLog/%s_%s.log" % (pipelineConfName, sha), "wb") as f:
            f.write(r.content)
            f.close
        print("buildLog/%s_%s.log" % (pipelineConfName, sha))


def analyze_failed_cause(index_dict, target_url):
    EXCODE = index_dict['EXCODE']
    filename = '%s_%s_%s.log' % (index_dict['ciName'], index_dict['commitId'],
                                 index_dict['createTime'])
    analysis_ci_index = {}
    analysis_ci_index['PR'] = index_dict['PR']
    analysis_ci_index['commitId'] = index_dict['commitId']
    analysis_ci_index['ciName'] = index_dict['ciName']
    analysis_ci_index['endTime'] = index_dict['endTime']
    analysis_ci_index['EXCODE'] = EXCODE
    analysis_ci_index['triggerUser'] = index_dict['triggerUser']
    analysis_ci_index['targetUrl'] = target_url
    document_fix = index_dict['documentfix']

    # 过滤commit包含关键字document_fix
    if document_fix == index_dict['documentfix'] == True:
        analysis_ci_index['description'] = 'document_fix'

    SkipTestCi = localConfig.cf.get('CIIndexScope', 'Paddle_skip_test_ci')
    PRECISION_TEST_CI = localConfig.cf.get('CIIndexScope',
                                           'Paddle_PRECISION_TEST')
    isSkipTest = 0
    isSkipDir = 0
    PRECISION_TEST = None
    PRECISION_TEST_Cases_count = None
    PRECISION_TEST_Cases_ratio = None
    notHitMapFiles = None

    if EXCODE in [0, 4]:  #2代码冲突，6需要approve, 4代码风格不符合
        isException = 0
    elif EXCODE == 2:
        isException = 0
        analysis_ci_index['description'] = 'code conflict'
    elif EXCODE == 6:
        isException = 0
        analysis_ci_index['description'] = 'pr need to approve'
    elif EXCODE == 503:
        isException = 1
        analysis_ci_index['description'] = 'HTTP PROXY NOT Good'
    elif EXCODE == 7:
        query_stat = "SELECT EXCODE,PR,commitId FROM paddle_ci_index WHERE ciName='%s' order by time desc limit 5" % index_dict[
            'ciName']
        db = Database()
        result = list(db.query(query_stat))
        if len(result) == 0:
            isException = 0
        else:
            last5tasks_buildfailed = [
                record['EXCODE'] for record in result[0]
                if record['EXCODE'] == 7
            ]
            if len(last5tasks_buildfailed) < 3:
                isException = 0
            else:
                isException = 1
    elif EXCODE == 8 and index_dict['ciName'] not in ['PR-CI-OP-benchmark'
                                                      ]:  #单测失败原因
        isException = 0  # 先默认是PR本身的单测问题
        testsfailed_list = []
        WLIST_PR = wlist_alarm.wlist_pr
        WLIST_UT = wlist_alarm.wlist_ut
        filename = '%s_%s.log' % (index_dict['ciName'], index_dict['commitId'])
        shortcommitId = index_dict['commitId'][0:7]
        f = open('buildLog/%s' % filename, 'r')
        data = f.read()
        if index_dict['ciName'].startswith('PR-CI-Py3') or index_dict[
                'ciName'].startswith('PR-CI-Coverage') or index_dict[
                    'ciName'].startswith('PR-CI-Mac'):  #Linux
            testsfailed_strlist = data.split('Summary Failed Tests...', 1)
            testsfailed = testsfailed_strlist[1].split(
                'The following tests FAILED:')[1].split('+ EXCODE=')[0]
        elif index_dict['ciName'].startswith('PR-CI-Windows') and index_dict[
                'ciName'] != 'PR-CI-Windows-Remain-BuildTest':  #Mac/Windows
            testsfailed_strlist = data.split('The following tests FAILED:', 1)
            testsfailed = testsfailed_strlist[1].split(
                'Errors while running CTest')[0]
        else:
            testsfailed_strlist = data.split('Summary Failed Tests...', 1)
            testsfailed = testsfailed_strlist[1].split(
                'The following tests FAILED:')[1].split('+ EXCODE=')[0]
        f.close()
        with open("buildLog/testsfailed_%s" % filename, "w") as t:
            t.write(testsfailed)
            t.close
        with open("buildLog/testsfailed_%s" % filename) as f:
            for line in f.readlines():
                tests = line[19:].strip().split('-')
                if len(tests) > 1:
                    tests_single = tests[1].strip()
                    testsfailed_list.append(tests_single)
            f.close()
        os.remove("buildLog/testsfailed_%s" % filename)
        if len(testsfailed_list) > 20:
            isException = 0
            analysis_ci_index['description'] = "PR's uts failed 20+"
            logger.error("PR's uts failed 20+: %s %s: %s" %
                         (index_dict['PR'], index_dict['ciName'], target_url))
        else:
            today = datetime.date.today()
            today_10_timestamp = int(
                time.mktime(time.strptime(str(today),
                                          '%Y-%m-%d'))) + 60 * 60 * 10
            if int(time.time()) < today_10_timestamp:
                yesterday = today - datetime.timedelta(days=1)
                date = yesterday.strftime('%Y%m%d')
            else:
                date = today.strftime('%Y%m%d')
            failed_cause_file = 'buildLog/failed_cause_%s.csv' % date
            rerun_failed_cause_file = 'buildLog/rerun_failed_cause_%s.csv' % date
            if os.path.exists(failed_cause_file) == False:
                create_failed_cause_csv(failed_cause_file)
            if os.path.exists(rerun_failed_cause_file) == False:
                create_failed_cause_csv(rerun_failed_cause_file)
            for t in testsfailed_list:
                df = pd.read_csv(failed_cause_file)
                IFRERUN = False
                failed_write_file = failed_cause_file
                for index, row in df.iterrows():
                    if index_dict['PR'] == row['PR'] and shortcommitId == row[
                            'COMMITID'] and t == row['FAILED_MESSAGE']:
                        IFRERUN = True
                if IFRERUN == True:
                    df = pd.read_csv(rerun_failed_cause_file)
                    failed_write_file = rerun_failed_cause_file
                if t in df['FAILED_MESSAGE'].values:
                    max_error_count = df[(
                        df['FAILED_MESSAGE'] == t)].sort_values(
                            by='ERROR_COUNT',
                            ascending=False).iloc[0]['ERROR_COUNT']
                    current_error_count = max_error_count + 1
                    data = {
                        'TIME':
                        time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                        'PR': index_dict['PR'],
                        'COMMITID': shortcommitId,
                        'CINAME': index_dict['ciName'],
                        'EXCODE': 8,
                        'FAILED_MESSAGE': [t],
                        'ERROR_COUNT': current_error_count,
                        'CIURL': target_url
                    }
                else:
                    data = {
                        'TIME':
                        time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                        'PR': index_dict['PR'],
                        'COMMITID': shortcommitId,
                        'CINAME': index_dict['ciName'],
                        'EXCODE': 8,
                        'FAILED_MESSAGE': [t],
                        'ERROR_COUNT': 1,
                        'CIURL': target_url
                    }
                logger.info('🌲 IFRERUN: %s data: %s' % (IFRERUN, data))
                write_data = pd.DataFrame(data)
                write_data.to_csv(failed_write_file, mode='a', header=False)
            df = pd.read_csv(failed_cause_file)
            alarm_ut_list = []
            alarm_ut_dict = {}
            for index, row in df.iterrows():
                if row['ERROR_COUNT'] > 2 and row[
                        'FAILED_MESSAGE'] not in alarm_ut_list and row[
                            'FAILED_MESSAGE'] not in WLIST_UT:
                    alarm_ut_list.append(row['FAILED_MESSAGE'])
            for ut in alarm_ut_list:
                alarm_ut_dict[ut] = []
            for index, row in df.iterrows():
                if row['FAILED_MESSAGE'] in alarm_ut_list:
                    alarm_ut_dict[row['FAILED_MESSAGE']].append(
                        '%s_%s_%s_%s' % (row['PR'], row['COMMITID'],
                                         row['CINAME'], row['CIURL']))
            alarm_ut_dict_ult = {}
            for ut in alarm_ut_dict:
                if len(alarm_ut_dict[ut]) > 2:
                    pr_list = []
                    for i in alarm_ut_dict[ut]:
                        pr = int(i.split('_')[0])
                        if pr not in WLIST_PR and pr not in pr_list:
                            pr_list.append(pr)
                    if len(pr_list) > 2:
                        alarm_ut_dict_ult[ut] = alarm_ut_dict[ut]
            logger.info('alarm_ut_dict_ult : %s' % alarm_ut_dict_ult)
            if len(alarm_ut_dict_ult) > 0:
                send_utfailed_mail(alarm_ut_dict_ult)
                isException = 1  #必挂
                analysis_ci_index['description'] = "ut failed certainly"

    elif EXCODE == 9:
        f = open('buildLog/%s' % filename, 'r')
        data = f.read()
        covfailed_strlist = data.split('expected >= 90.0 %, actual', 1)
        covRate = float(covfailed_strlist[1].split('%, failed')[0].strip())
        analysis_ci_index['covRate'] = covRate
        analysis_ci_index[
            'description'] = 'Coverage Rate NOT Reach The Standard'
        isException = 0

    elif EXCODE == 1:
        isException = 0  #EXCODE==1时暂定为非异常

    if index_dict['ciName'] in SkipTestCi:
        f = open('buildLog/%s' % filename, 'r')
        data = f.read()
        if 'paddle whl does not diff in PR-CI-Model-benchmark, so skip this ci' in data:
            isSkipTest = 1
        if 'ipipe_log_param_isSkipDir_model_benchmark' in data:
            isSkipDir = 1

    # 获取精准测试监控指标
    if index_dict['ciName'] in PRECISION_TEST_CI:
        f = open('buildLog/%s' % filename, 'r')
        data = f.read()
        if 'ipipe_log_param_PRECISION_TEST_Cases_count' in data:
            PRECISION_TEST_Cases_count = data.split(
                'ipipe_log_param_PRECISION_TEST_Cases_count:', 1)
            PRECISION_TEST_Cases_count = PRECISION_TEST_Cases_count[1:][
                0].split('\n')[0].strip()
        if 'ipipe_log_param_PRECISION_TEST_Cases_ratio' in data:
            PRECISION_TEST_Cases_ratio = data.split(
                'ipipe_log_param_PRECISION_TEST_Cases_ratio:', 1)
            PRECISION_TEST_Cases_ratio = PRECISION_TEST_Cases_ratio[1:][
                0].split('\n')[0].strip()
        if 'notHitMapFiles' in data:
            notHitMapFiles = data.split('notHitMapFiles:', 1)
            notHitMapFiles = notHitMapFiles[1:][0].split('\n')[0].strip()
        if 'ipipe_log_param_PRECISION_TEST' in data:
            PRECISION_TEST = data.split('ipipe_log_param_PRECISION_TEST:', 1)
            PRECISION_TEST = PRECISION_TEST[1:][0].split('\n')[0].strip()
            if PRECISION_TEST == 'false':
                PRECISION_TEST = False
            elif PRECISION_TEST == 'true':
                PRECISION_TEST = True

    analysis_ci_index['isException'] = isException
    analysis_ci_index['isSkipTest'] = isSkipTest
    analysis_ci_index['isSkipDir'] = isSkipDir
    analysis_ci_index['PRECISION_TEST'] = PRECISION_TEST
    analysis_ci_index['PRECISION_TEST_count'] = PRECISION_TEST_Cases_count
    analysis_ci_index['PRECISION_TEST_ratio'] = PRECISION_TEST_Cases_ratio
    analysis_ci_index['PRECISION_TEST_notHitMapFiles'] = notHitMapFiles
    logger.info("EXCODE: %s, isException: %s" % (EXCODE, isException))
    logger.info("analysis_ci_index: %s" % analysis_ci_index)
    db = Database()
    result = db.insert('paddle_ci_analysis', analysis_ci_index)
    if result == True:
        logger.info('%s insert paddle_ci_analysis success!' %
                    analysis_ci_index)
    else:
        logger.info('%s insert paddle_ci_analysis failed!' % analysis_ci_index)


def send_utfailed_mail(alarm_ut_dict):
    with open("buildLog/lastestfaileduts.json", 'r') as load_f:
        try:
            lastestfaileduts = json.load(load_f)
        except json.decoder.JSONDecodeError:
            lastestfaileduts = {}
    load_f.close()
    if alarm_ut_dict == lastestfaileduts:
        logger.info('No new failed task!')
    else:
        with open("buildLog/lastestfaileduts.json", "w") as f:
            json.dump(alarm_ut_dict, f)
            f.close
        HTML_CONTENT = "<html> <head></head> <body>  <p>Hi, ALL:</p>  <p>以下单测已经在今天挂在3个不同的PR，请QA同学及时revert或disable该单测，并进行排查。</p><p>ps: 绿色背景的数据是本次新增的失败单测。</p>"
        TABLE_CONTENT = '<table border="1" align="center"> <caption> <font size="3"><b>单测失败列表</b></font>  </caption> <tbody> <tr align="center"> <td bgcolor="#d0d0d0">单测</td> <td bgcolor="#d0d0d0">PR</td> <td bgcolor="#d0d0d0"> commitID</td> <td bgcolor="#d0d0d0"> CIName</td> <td bgcolor="#d0d0d0">xly_url</td></tr> '
        for ut in alarm_ut_dict:
            for l in alarm_ut_dict[ut]:
                message = l.split('_')
                pr = message[0]
                commit = message[1]
                ciname = message[2]
                ciurl = message[3]
                if ut not in lastestfaileduts:
                    TABLE_CONTENT += '<tr align="center" bgcolor="#b5c4b1"><td> %s</td><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (
                        ut, pr, commit, ciname, ciurl)
                else:
                    if l not in lastestfaileduts[ut]:
                        TABLE_CONTENT += '<tr align="center" bgcolor="#b5c4b1"><td> %s</td><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (
                            ut, pr, commit, ciname, ciurl)
                    else:
                        TABLE_CONTENT += '<tr align="center"><td> %s</td><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (
                            ut, pr, commit, ciname, ciurl)
        HTML_CONTENT = HTML_CONTENT + TABLE_CONTENT + "</tbody> </table> </body></html> "
        receiver = ['ddd@baidu.com']
        title = '[告警] CI单测挂了三次以上！'
        sendMail(receiver, title, HTML_CONTENT)


def sendMail(receiver, title, content):
    """发送邮件"""
    mail = Mail()
    mail.set_sender('paddlepaddle_bot@163.com')
    mail.set_receivers(receiver)
    mail.set_title(title)
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()


def create_failed_cause_csv(failed_cause_file):
    df = pd.DataFrame(columns=[
        'TIME', 'PR', 'COMMITID', 'CINAME', 'EXCODE', 'FAILED_MESSAGE',
        'ERROR_COUNT', 'CIURL'
    ])
    df.to_csv(failed_cause_file)
