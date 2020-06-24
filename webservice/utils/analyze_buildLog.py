#coding=utf-8
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from utils.readConfig import ReadConfig
from utils.auth_ipipe import Get_ipipe_auth
from utils.db import Database
from utils import bosclient
import os
import time
import datetime
import logging
from tornado.httpclient import AsyncHTTPClient

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


def generateCiIndex(repo, sha, target_url):
    if target_url.startswith('http://10.87.145.41:8111'):
        analyze_teamcity_log(target_url)
    elif target_url.startswith('https://xly.bce.baidu.com'):
        analyze_ipipe_log(sha, target_url)


def analyze_teamcity_log(target_url):
    pass


def analyze_ipipe_log(sha, target_url):
    index_dict = {}
    pipelineBuildid = target_url.split('/')[-3]
    stage_url = localConfig.cf.get('ipipeConf', 'stage_url') + pipelineBuildid
    session, req = Get_ipipe_auth(stage_url)
    try:
        res = session.send(req).json()
    except Exception as e:
        print("Error: %s" % e)
    else:
        pipelineConfName = res['pipelineConfName']
        jobGroupBuildBeans = res['pipelineBuildBean']['stageBuildBeans'][0][
            'jobGroupBuildBeans'][0]
        PR = res['pipelineBuildBean']['stageBuildBeans'][0]['outParams'][
            'AGILE_PULL_ID']
        createTime = get_commit_createTime(sha)
        index_dict['PR'] = int(PR)
        index_dict['commitId'] = sha
        index_dict['createTime'] = createTime
        for job in jobGroupBuildBeans:
            jobName = job['jobName']
            if jobName not in ['构建镜像', 'build-docker-image']:
                logParam = job['realJobBuild']['logUrl']
                startTime = int(str(job['startTime'])[:-3])
                endTime = int(str(job['endTime'])[:-3])
                index_dict['startTime'] = startTime
                index_dict['endTime'] = endTime
                logUrl = localConfig.cf.get('ipipeConf', 'log_url') + logParam
                getIpipeBuildLog(index_dict, sha, pipelineConfName, logUrl)


def getIpipeBuildLog(index_dict, sha, pipelineConfName, logUrl):
    try:
        r = requests.get(logUrl)
    except Exception as e:
        print("Error: %s" % e)
    else:
        with open("buildLog/%s_%s.log" % (pipelineConfName, sha), "wb") as f:
            f.write(r.content)
            f.close()
            get_index(index_dict, sha, pipelineConfName)
    os.remove("buildLog/%s_%s.log" % (pipelineConfName, sha))


def get_index(index_dict, sha, pipelineConfName):
    ifInsert = True
    db = Database()
    filename = '%s_%s.log' % (pipelineConfName, sha)
    index_dict['ciName'] = pipelineConfName
    f = open('buildLog/%s' % filename, 'r')
    logger.info('filename: %s; PR: %s' % (filename, index_dict['PR']))
    data = f.read()
    buildTime_strlist = data.split('Build Time:', 1)
    buildTime = buildTime_strlist[1:][0].split('s')[0].strip()
    index_dict['buildTime'] = float(buildTime)
    if filename.startswith('PR-CI-Inference'):
        fluidInferenceSize_strlist = data.split('FLuid_Inference Size:', 1)
        fluidInferenceSize = fluidInferenceSize_strlist[1:][0].split('M')[
            0].strip()
        index_dict['fluidInferenceSize'] = float(fluidInferenceSize)
        testFluidLibTime_strlist = data.split('test_fluid_lib Total Time:', 1)
        testFluidLibTime = testFluidLibTime_strlist[1:][0].split('s')[0].strip(
        )
        index_dict['testFluidLibTime'] = float(testFluidLibTime)
        testFluidLibTrainTime_strlist = data.split(
            'test_fluid_lib_train Total Time:', 1)
        testFluidLibTrainTime = testFluidLibTrainTime_strlist[1:][0].split(
            's')[0].strip()
        index_dict['testFluidLibTrainTime'] = float(testFluidLibTrainTime)
    elif filename.startswith('PR-CI-Coverage') or filename.startswith(
            'PR-CI-Py35'):
        buildSize_strlist = data.split('Build Size:', 1)
        buildSize = buildSize_strlist[1:][0].split('G')[0].strip()
        index_dict['buildSize'] = float(buildSize)
        WhlSize_strlist = data.split('PR whl Size:', 1)
        WhlSize = WhlSize_strlist[1:][0].split('M')[0].strip()
        index_dict['WhlSize'] = float(WhlSize)
        testCaseCount_single_strlist = data.split('1 card TestCases count is')
        testCaseCount_single = 0
        for item in testCaseCount_single_strlist[1:]:  #原因是单卡的case分了两部分
            testCaseCount_single += int(item.split('\n')[0].strip())
        index_dict['testCaseCount_single'] = testCaseCount_single
        testCaseCount_multi_strlist = data.split('2 card TestCases count is')
        testCaseCount_multi = int(testCaseCount_multi_strlist[1:][0].split(
            '\n')[0].strip())
        index_dict['testCaseCount_multi'] = testCaseCount_multi
        testCaseCount_exclusive_strlist = data.split(
            'exclusive TestCases count is')
        testCaseCount_exclusive = int(testCaseCount_exclusive_strlist[1:][0]
                                      .split('\n')[0].strip())
        index_dict['testCaseCount_exclusive'] = testCaseCount_exclusive
        testCaseCount_total = testCaseCount_single + testCaseCount_multi + testCaseCount_exclusive
        index_dict['testCaseCount_total'] = testCaseCount_total
        testCaseTime_single_strlist = data.split(
            '1 card TestCases Total Time:')
        testCaseTime_single = 0
        for item in testCaseTime_single_strlist[1:]:  #原因是单卡的case分了两部分
            testCaseTime_single += int(item.split('s')[0].strip())
        index_dict['testCaseTime_single'] = testCaseTime_single
        testCaseTime_multi_strlist = data.split('2 card TestCases Total Time:')
        testCaseTime_multi = int(testCaseTime_multi_strlist[1:][0].split('s')[
            0].strip())
        index_dict['testCaseTime_multi'] = testCaseTime_multi
        testCaseTime_exclusive_strlist = data.split(
            'exclusive TestCases Total Time:')
        testCaseTime_exclusive = int(testCaseTime_exclusive_strlist[1:][0]
                                     .split('s')[0].strip())
        index_dict['testCaseTime_exclusive'] = testCaseTime_exclusive
        testCaseTime_total_strlist = data.split('TestCases Total Time:')
        testCaseTime_total = 0
        for item in testCaseTime_total_strlist[1:]:
            testCaseTime_total = int(item.split('s')[0].strip()) if int(
                item.split('s')[0].strip(
                )) > testCaseTime_total else testCaseTime_total
        index_dict['testCaseTime_total'] = testCaseTime_total
    insertTime = int(time.time())
    query_stat = "SELECT * FROM paddle_ci_index WHERE ciName='%s' and commitId='%s' and PR=%s order by time desc" % (
        index_dict['ciName'], index_dict['commitId'], index_dict['PR'])
    queryTime = ifAlreadyExist(query_stat)
    if queryTime != '':
        ifInsert = False if insertTime - queryTime < 30 else True
    if ifInsert == True:
        result = db.insert('paddle_ci_index', index_dict)
        if result == True:
            logger.info('%s %s %s insert paddle_ci_index success!' %
                        (pipelineConfName, index_dict['PR'], sha))
        else:
            logger.info('%s %s %s insert paddle_ci_index failed!' %
                        (pipelineConfName, index_dict['PR'], sha))


def get_commit_createTime(sha):
    """get commit createtime"""
    url = 'https://api.github.com/repos/PaddlePaddle/Paddle/commits/%s' % sha
    headers = {
        'authorization': "auth message",
        'accept': "application/vnd.github.antiope-preview+json",
        'content-type': "application/json"
    }
    response = requests.request("GET", url, headers=headers).json()
    commitTime = response['commit']['committer']['date']
    commitTime = commitTime.replace('T', ' ').replace('Z',
                                                      '')  #java time To string
    commitTime = time.strptime(commitTime, '%Y-%m-%d %H:%M:%S')
    dt = datetime.datetime.fromtimestamp(time.mktime(commitTime))
    actualCreateTime = (
        dt + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    timeArray = time.strptime(actualCreateTime, "%Y-%m-%d %H:%M:%S")
    createTime = int(time.mktime(timeArray))
    return createTime
