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


def sendMail(receiver, title, content):
    """发送邮件"""
    mail = Mail()
    mail.set_sender('paddlepaddle_bot@163.com')
    mail.set_receivers(receiver)
    mail.set_title(title)
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()


class analysisBuildLog(object):
    def __init__(self, repo, sha, target_url):
        self.repo = repo
        self.sha = sha
        self.target_url = target_url
        self.Paddle_build_parallel_ci = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_build_parallel_ci')
            .split(','))
        self.Paddle_cpu_gpu_separate_ci_tuple = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_cpu_gpu_separate_ci')
            .split(','))
        self.Paddle_container_ci = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_container_ci').split(
                ','))
        self.Other_sa_ci_tuple = tuple(
            localConfig.cf.get('CIIndexScope', 'Other_sa_ci').split(','))
        self.Other_container_ci = tuple(
            localConfig.cf.get('CIIndexScope', 'Other_container_ci').split(
                ','))
        self.EXCODE_DICT = {
            'docker_build_failed': 64,
            'clone_code_failed': 63,
            'temporary_files_failed': 65,
            'build_failed': 7,
            'test_failed': 8,
            'coverage_failed': 9,
            'http_proxy_failed': 503,
            'approve_failed': 6,
            'code_style_failed': 4,
            'code_conflict': 2,
            'code_too_old': 15
        }
        self.SkipTestCi_tuple = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_skip_test_ci').split(
                ','))
        self.PRECISION_TEST_CI_tuple = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_PRECISION_TEST').split(
                ','))
        self.Paddle_testFailed_analysis_ci_tuple = tuple(
            localConfig.cf.get('CIIndexScope', 'Paddle_testFailed_analysis_ci')
            .split(','))
        self.db = Database()

    def get_stageUrl(self):
        pipelineBuildid = self.target_url.split('/')[-3]
        stage_url = localConfig.cf.get('ipipeConf',
                                       'stage_url') + pipelineBuildid
        return stage_url

    def getIpipeBuildLog(self, pipelineConfName, createTime, logUrl, typ=None):
        try:
            r = requests.get(logUrl)
        except Exception as e:
            print("Error: %s" % e)
        else:
            if typ == 'cpu':
                filename = "buildLog/%s_%s_%s_cpu.log" % (pipelineConfName,
                                                          self.sha, createTime)
            elif typ == 'gpu':
                filename = "buildLog/%s_%s_%s_gpu.log" % (pipelineConfName,
                                                          self.sha, createTime)
            else:
                filename = "buildLog/%s_%s_%s.log" % (pipelineConfName,
                                                      self.sha, createTime)
            with open(filename, "wb") as f:
                f.write(r.content)
                f.close()

    def getContainerCIIndex(self, stageBuildBeans):
        ContainerCIIndex = {}
        for stage in stageBuildBeans:
            stageName = stage['stageName']
            jobGroupBuildBeans = stage['jobGroupBuildBeans'][0]
            if stageName == 'clone code':
                clone_code_status = jobGroupBuildBeans[0]['status']
                clone_code_startTime = int(
                    str(jobGroupBuildBeans[0]['realJobBuild']['shellBuild'][
                        'startTime'])[:-3])
                clone_code_endTime = int(
                    str(jobGroupBuildBeans[0]['realJobBuild']['shellBuild'][
                        'endTime'])[:-3])
                ContainerCIIndex['clone_code_status'] = clone_code_status
                ContainerCIIndex['clone_code_startTime'] = clone_code_startTime
                ContainerCIIndex['clone_code_endTime'] = clone_code_endTime
            else:
                for job in jobGroupBuildBeans:
                    if job['jobName'] == 'Git-clone':
                        clone_code_status = job['status']
                        clone_code_startTime = int(
                            str(job['realJobBuild']['shellBuild']['startTime'])
                            [:-3])
                        clone_code_endTime = int(
                            str(job['realJobBuild']['shellBuild']['endTime'])
                            [:-3])
                        ContainerCIIndex[
                            'clone_code_status'] = clone_code_status
                        ContainerCIIndex[
                            'clone_code_startTime'] = clone_code_startTime
                        ContainerCIIndex[
                            'clone_code_endTime'] = clone_code_endTime
                    elif job['jobName'] in ['构建镜像', 'build-docker-image']:
                        docker_build_status = job['status']
                        docker_build_startTime = int(
                            str(job['realJobBuild']['startTime'])[:-3])
                        docker_build_endTime = int(
                            str(job['realJobBuild']['endTime'])[:-3])
                        ContainerCIIndex[
                            'docker_build_status'] = docker_build_status
                        ContainerCIIndex[
                            'docker_build_startTime'] = docker_build_startTime
                        ContainerCIIndex[
                            'docker_build_endTime'] = docker_build_endTime
                    elif job['jobName'] == 'paddle-build':
                        cpu_build_status = job['status']
                        cpu_build_startTime = int(
                            str(job['realJobBuild']['startTime'])
                            [:-3]) if cpu_build_status != 'WAITTING' else 0
                        cpu_build_endTime = int(
                            str(job['realJobBuild']['endTime'])
                            [:-3]) if cpu_build_status != 'WAITTING' else 0
                        logParam = job['realJobBuild']['logUrl']
                        cpu_logUrl = localConfig.cf.get(
                            'ipipeConf', 'log_url'
                        ) + logParam if cpu_build_status != 'WAITTING' else None
                        ContainerCIIndex['cpu_build_status'] = cpu_build_status
                        ContainerCIIndex[
                            'cpu_build_startTime'] = cpu_build_startTime
                        ContainerCIIndex[
                            'cpu_build_endTime'] = cpu_build_endTime
                        ContainerCIIndex['cpu_logUrl'] = cpu_logUrl
                    elif job['jobName'] == 'paddle-test':
                        gpu_test_status = job['status']
                        gpu_test_startTime = int(
                            str(job['realJobBuild']['startTime'])
                            [:-3]) if gpu_test_status != 'WAITTING' else 0
                        gpu_test_endTime = int(
                            str(job['realJobBuild']['endTime'])
                            [:-3]) if gpu_test_status != 'WAITTING' else 0
                        logParam = job['realJobBuild']['logUrl']
                        gpu_logUrl = localConfig.cf.get(
                            'ipipeConf', 'log_url'
                        ) + logParam if gpu_test_status != 'WAITTING' else None
                        ContainerCIIndex['gpu_test_status'] = gpu_test_status
                        ContainerCIIndex[
                            'gpu_test_startTime'] = gpu_test_startTime
                        ContainerCIIndex['gpu_test_endTime'] = gpu_test_endTime
                        ContainerCIIndex['gpu_logUrl'] = gpu_logUrl
                    else:
                        paddle_build_status = job['status']
                        paddle_build_startTime = int(
                            str(job['realJobBuild']['startTime'])
                            [:-3]) if paddle_build_status != 'WAITTING' else 0
                        paddle_build_endTime = int(
                            str(job['realJobBuild']['endTime'])
                            [:-3]) if paddle_build_status != 'WAITTING' else 0
                        logParam = job['realJobBuild']['logUrl']
                        logUrl = localConfig.cf.get(
                            'ipipeConf', 'log_url'
                        ) + logParam if paddle_build_status != 'WAITTING' else None
                        ContainerCIIndex[
                            'paddle_build_status'] = paddle_build_status
                        ContainerCIIndex[
                            'paddle_build_startTime'] = paddle_build_startTime
                        ContainerCIIndex[
                            'paddle_build_endTime'] = paddle_build_endTime
                        ContainerCIIndex['logUrl'] = logUrl
        return ContainerCIIndex

    def getSaCIIndex(self, stageBuildBeans):
        SaCIIndex = {}
        jobExecTime = 0
        for stage in stageBuildBeans:
            jobGroupBuildBeans = stage['jobGroupBuildBeans'][0]
            for job in jobGroupBuildBeans:
                if job['jobName'] == 'Git-clone':
                    clone_code_status = job['status']
                    clone_code_startTime = int(
                        str(job['realJobBuild']['shellBuild']['startTime'])
                        [:-3])
                    clone_code_endTime = int(
                        str(job['realJobBuild']['shellBuild']['endTime'])[:-3])
                    SaCIIndex['clone_code_status'] = clone_code_status
                    SaCIIndex['clone_code_startTime'] = clone_code_startTime
                    SaCIIndex['clone_code_endTime'] = clone_code_endTime
                else:
                    job_status = job['status']
                    job_startTime = int(
                        str(job['realJobBuild']['shellBuild']['startTime'])
                        [:-3]) if job['status'] != 'WAITTING' else 0
                    job_endTime = int(
                        str(job['realJobBuild']['shellBuild']['endTime'])
                        [:-3]) if job['status'] != 'WAITTING' else 0
                    jobExecTime = jobExecTime + (job_endTime - job_startTime)
                    taskid = job['realJobBuild']['shellBuild']['taskId']
                    logUrl = "https://xly.bce.baidu.com/paddlepaddle/paddle-ci/sa_log/log/download/%s" % taskid

        SaCIIndex['job_startTime'] = job_startTime
        SaCIIndex['job_endTime'] = job_endTime
        SaCIIndex['jobExecTime'] = jobExecTime
        SaCIIndex['logUrl'] = logUrl
        SaCIIndex['job_status'] = job_status
        return SaCIIndex

    def getBuildParallelCIIndex(self, stageBuildBeans):
        BuildParallelCIIndex = {}
        for stage in stageBuildBeans:
            stageName = stage['stageName']
            BuildParallelCIIndex[stageName] = {}
            jobGroupBuildBeans = stage['jobGroupBuildBeans']
            for Beans in jobGroupBuildBeans:
                for job in Beans:
                    BuildParallelCIIndex[stageName][job['jobName']] = {}
                    BuildParallelCIIndex[stageName][job['jobName']][
                        'status'] = job['status']
                    if job['jobType'] == 'MULTI_PIPELINE_PLUGIN':
                        pass
                    elif job['jobName'] == 'Git-clone':
                        BuildParallelCIIndex[stageName][job['jobName']][
                            'startTime'] = int(
                                str(job['realJobBuild']['shellBuild'][
                                    'startTime'])[:-3])
                        BuildParallelCIIndex[stageName][job['jobName']][
                            'endTime'] = int(
                                str(job['realJobBuild']['shellBuild'][
                                    'endTime'])[:-3])
                    else:
                        BuildParallelCIIndex[stageName][job['jobName']][
                            'startTime'] = int(
                                str(job['realJobBuild']['startTime'])
                                [:-3]) if job['status'] != 'WAITTING' else 0
                        BuildParallelCIIndex[stageName][job['jobName']][
                            'endTime'] = int(
                                str(job['realJobBuild']['endTime'])
                                [:-3]) if job['status'] != 'WAITTING' else 0
                        BuildParallelCIIndex[stageName][job['jobName']][
                            'logUrl'] = localConfig.cf.get(
                                'ipipeConf', 'log_url') + job['realJobBuild'][
                                    'logUrl'] if job[
                                        'status'] != 'WAITTING' else None
        return BuildParallelCIIndex

    def getBasicCIIndex(self, ciName):
        """
        获取CI基础指标: 时间 + 状态 + 退出码
        1. 退出码的获取需要分析日志
        """
        basic_ci_index_dict = {}
        stage_url = self.get_stageUrl()
        session, req = Get_ipipe_auth(stage_url)
        try:
            res = session.send(req).json()
        except Exception as e:
            print("Error: %s" % e)
        else:
            branch = res['branch']
            basic_ci_index_dict['branch'] = branch
            PR = res['pipelineBuildBean']['stageBuildBeans'][0]['outParams'][
                'AGILE_PULL_ID']
            basic_ci_index_dict['PR'] = PR
            commit_createTime = int(
                str(res['pipelineBuildBean']['startTime'])
                [:-3])  #commit提交时间/rerun时间
            basic_ci_index_dict['commit_createTime'] = commit_createTime
            if res["pipelineBuildBean"]["reason"] == 'SKIP':
                basic_ci_index_dict['EXCODE'] = 0
                basic_ci_index_dict['waitTime_total'] = 0  #排队总时间
                basic_ci_index_dict['execTime_total'] = 0  #执行总时间
                return basic_ci_index_dict
            stageBuildBeans = res['pipelineBuildBean']['stageBuildBeans']
            if self.repo != 'PaddlePaddle/Paddle':
                if res['pipelineConfName'].startswith(self.Other_container_ci):
                    CIIndex = self.getContainerCIIndex(stageBuildBeans)
                else:
                    CIIndex = self.getSaCIIndex(stageBuildBeans)
            else:
                if res['pipelineConfName'].startswith(
                        self.Paddle_build_parallel_ci):
                    CIIndex = self.getBuildParallelCIIndex(stageBuildBeans)
                elif res['pipelineConfName'].startswith(
                        self.Paddle_container_ci):
                    CIIndex = self.getContainerCIIndex(stageBuildBeans)
                else:
                    CIIndex = self.getSaCIIndex(stageBuildBeans)
            testScope = []
            if 'jobExecTime' in CIIndex:  #sa任务
                if 'clone_code_status' in CIIndex:
                    waitTime_total = (CIIndex['clone_code_startTime'] -
                                      commit_createTime) + (
                                          CIIndex['job_startTime'] -
                                          CIIndex['clone_code_endTime'])
                    execTime_total = (CIIndex['jobExecTime']
                                      ) + (CIIndex['clone_code_endTime'] -
                                           CIIndex['clone_code_startTime'])
                    basic_ci_index_dict['clone_code_startTime'] = CIIndex[
                        'clone_code_startTime']
                    basic_ci_index_dict['clone_code_endTime'] = CIIndex[
                        'clone_code_endTime']
                    basic_ci_index_dict['paddle_build_startTime'] = CIIndex[
                        'job_startTime']
                    basic_ci_index_dict['paddle_build_endTime'] = CIIndex[
                        'job_endTime']
                    if CIIndex['clone_code_status'] == 'FAIL':
                        EXCODE = self.EXCODE_DICT['clone_code_failed']
                        basic_ci_index_dict['EXCODE'] = EXCODE
                        return basic_ci_index_dict
                else:
                    basic_ci_index_dict['paddle_build_startTime'] = CIIndex[
                        'job_startTime']
                    basic_ci_index_dict['paddle_build_endTime'] = CIIndex[
                        'job_endTime']
                    waitTime_total = CIIndex[
                        'job_startTime'] - commit_createTime if CIIndex[
                            'job_startTime'] != 0 else 0
                    execTime_total = CIIndex['jobExecTime']
                if self.repo not in ['PaddlePaddle/Paddle']:
                    EXCODE = 0 if CIIndex['job_status'] == 'SUCC' else 1
                elif res['pipelineConfName'].startswith(
                        self.Paddle_sa_ci) and not res[
                            'pipelineConfName'].startswith(
                                self.Paddle_sa_detailed_ci):
                    EXCODE = 0 if CIIndex['job_status'] == 'SUCC' else 1
                else:
                    if CIIndex['logUrl'] != None and self.repo in [
                            'PaddlePaddle/Paddle'
                    ]:
                        self.getIpipeBuildLog(res['pipelineConfName'],
                                              commit_createTime,
                                              CIIndex['logUrl'])
                        log_filename = "buildLog/%s_%s_%s.log" % (
                            res['pipelineConfName'], self.sha,
                            commit_createTime)
                        EXCODE = self.getExcode(res['pipelineConfName'],
                                                log_filename)

            elif ciName.startswith(self.Paddle_build_parallel_ci):
                for stage in CIIndex:
                    for job in CIIndex[stage]:
                        if job == '流水线复用插件':
                            pass
                        elif job == 'Git-clone':
                            clone_code_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'clone_code_startTime'] = CIIndex[stage][job][
                                    'startTime']
                            basic_ci_index_dict[
                                'clone_code_endTime'] = CIIndex[stage][job][
                                    'endTime']
                            waitTime_total = basic_ci_index_dict[
                                'clone_code_startTime'] - commit_createTime
                            execTime_total = basic_ci_index_dict[
                                'clone_code_endTime'] - basic_ci_index_dict[
                                    'clone_code_startTime']
                            EXCODE = self.EXCODE_DICT[
                                'clone_code_failed'] if clone_code_status == 'FAIL' else 0
                        elif job in ['构建镜像', 'build-docker-image']:
                            build_docker_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'docker_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'docker_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                            if build_docker_status == 'FAIL':
                                waitTime_total = basic_ci_index_dict[
                                    'docker_build_startTime'] - commit_createTime
                                execTime_total = basic_ci_index_dict[
                                    'docker_build_endTime'] - basic_ci_index_dict[
                                        'docker_build_startTime']
                                EXCODE = self.EXCODE_DICT[
                                    'docker_build_failed']
                        elif job == 'paddle-build':
                            paddle_build_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'paddle_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'paddle_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                            if self.repo in [
                                    'PaddlePaddle/Paddle'
                            ] and CIIndex[stage][job]['logUrl'] != None:
                                self.getIpipeBuildLog(
                                    res['pipelineConfName'], commit_createTime,
                                    CIIndex[stage][job]['logUrl'], 'cpu')
                            waitTime_total = (
                                basic_ci_index_dict['docker_build_startTime'] -
                                commit_createTime
                            ) + (basic_ci_index_dict['paddle_build_startTime']
                                 - basic_ci_index_dict['docker_build_endTime'])
                            execTime_total = (
                                basic_ci_index_dict['docker_build_endTime'] -
                                basic_ci_index_dict['docker_build_startTime']
                            ) + (basic_ci_index_dict['paddle_build_endTime'] -
                                 basic_ci_index_dict['paddle_build_startTime'])
                            log_filename = "buildLog/%s_%s_%s_cpu.log" % (
                                res['pipelineConfName'], self.sha,
                                commit_createTime)
                            EXCODE = self.getExcode(
                                res['pipelineConfName'], log_filename
                            ) if paddle_build_status == 'FAIL' else 0
                        else:
                            testScope.append(job)
                            basic_ci_index_dict['%s_startTime' % job.replace(
                                '-', '_')] = CIIndex[stage][job]['startTime']
                            basic_ci_index_dict['%s_endTime' % job.replace(
                                '-', '_')] = CIIndex[stage][job]['endTime']
                            if self.repo in [
                                    'PaddlePaddle/Paddle'
                            ] and CIIndex[stage][job]['logUrl'] != None:
                                self.getIpipeBuildLog(
                                    '%s_%s' % (res['pipelineConfName'],
                                               job.replace('-', '_')),
                                    commit_createTime,
                                    CIIndex[stage][job]['logUrl'], 'gpu')
                if len(testScope) != 0:
                    ##gputest 执行时间选耗时长的 等待时间选等待最长的？？合理吗？
                    gpu_waitTime = 0
                    gpu_execTime = 0
                    gpu_excode = []
                    for test in testScope:
                        test = test.replace('-', '_')
                        gpu_waitTime_tem = basic_ci_index_dict[
                            '%s_startTime' %
                            test] - basic_ci_index_dict['docker_build_endTime']
                        if gpu_waitTime_tem > gpu_waitTime:
                            gpu_waitTime = gpu_waitTime_tem
                        gpu_execTime_tem = basic_ci_index_dict[
                            '%s_endTime' %
                            test] - basic_ci_index_dict['%s_startTime' % test]
                        if gpu_execTime_tem > gpu_execTime:
                            gpu_execTime = gpu_execTime_tem
                        log_filename = "buildLog/%s_%s_%s_%s_gpu.log" % (
                            res['pipelineConfName'], test.replace('-', '_'),
                            self.sha, commit_createTime)
                        if test == 'paddle_test' or len(testScope) == 1:
                            EXCODE = self.getExcode(res['pipelineConfName'],
                                                    log_filename)
                        else:
                            if test.split('_')[1] == 'infer':
                                EXCODE_infer = self.getExcode(
                                    res['pipelineConfName'], log_filename)
                                basic_ci_index_dict[
                                    'EXCODE_infer'] = EXCODE_infer
                    waitTime_total = (
                        basic_ci_index_dict['docker_build_startTime'] -
                        commit_createTime) + gpu_waitTime
                    execTime_total = (
                        basic_ci_index_dict['docker_build_endTime'] -
                        basic_ci_index_dict['docker_build_startTime']
                    ) + gpu_execTime

            elif ciName.startswith(self.Paddle_cpu_gpu_separate_ci_tuple):
                for stage in CIIndex:
                    for job in CIIndex[stage]:
                        if job == 'Git-clone':
                            clone_code_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'clone_code_startTime'] = CIIndex[stage][job][
                                    'startTime']
                            basic_ci_index_dict[
                                'clone_code_endTime'] = CIIndex[stage][job][
                                    'endTime']
                        elif job in ['构建镜像', 'build-docker-image']:
                            build_docker_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'docker_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'docker_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                        elif job == 'paddle-build':
                            paddle_build_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'paddle_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'paddle_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                            if self.repo in [
                                    'PaddlePaddle/Paddle'
                            ] and CIIndex[stage][job]['logUrl'] != None:
                                self.getIpipeBuildLog(
                                    res['pipelineConfName'], commit_createTime,
                                    CIIndex[stage][job]['logUrl'], 'cpu')
                        else:
                            testScope.append(job)
                            basic_ci_index_dict['%s_startTime' % job.replace(
                                '-', '_')] = CIIndex[stage][job]['startTime']
                            basic_ci_index_dict['%s_endTime' % job.replace(
                                '-', '_')] = CIIndex[stage][job]['endTime']

                            if self.repo in [
                                    'PaddlePaddle/Paddle'
                            ] and CIIndex[stage][job]['logUrl'] != None:
                                self.getIpipeBuildLog(
                                    '%s_%s' % (res['pipelineConfName'],
                                               job.replace('-', '_')),
                                    commit_createTime,
                                    CIIndex[stage][job]['logUrl'], 'gpu')

                if clone_code_status == 'FAIL':
                    waitTime_total = basic_ci_index_dict[
                        'clone_code_startTime'] - commit_createTime
                    execTime_total = basic_ci_index_dict[
                        'clone_code_endTime'] - basic_ci_index_dict[
                            'clone_code_startTime']
                    EXCODE = self.EXCODE_DICT['clone_code_failed']
                elif build_docker_status == 'FAIL':
                    waitTime_total = (
                        basic_ci_index_dict['clone_code_startTime'] -
                        commit_createTime) + (
                            basic_ci_index_dict['docker_build_startTime'] -
                            basic_ci_index_dict['clone_code_endTime'])
                    execTime_total = (
                        basic_ci_index_dict['clone_code_endTime'] -
                        basic_ci_index_dict['clone_code_startTime']) + (
                            basic_ci_index_dict['docker_build_endTime'] -
                            basic_ci_index_dict['docker_build_startTime'])
                    EXCODE = self.EXCODE_DICT['docker_build_failed']
                elif paddle_build_status == 'FAIL':
                    waitTime_total = (
                        basic_ci_index_dict['clone_code_startTime'] -
                        commit_createTime) + (
                            basic_ci_index_dict['docker_build_startTime'] -
                            basic_ci_index_dict['clone_code_endTime']) + (
                                basic_ci_index_dict['paddle_build_startTime'] -
                                basic_ci_index_dict['docker_build_endTime'])
                    execTime_total = (
                        basic_ci_index_dict['clone_code_endTime'] -
                        basic_ci_index_dict['clone_code_startTime']) + (
                            basic_ci_index_dict['docker_build_endTime'] -
                            basic_ci_index_dict['docker_build_startTime']) + (
                                basic_ci_index_dict['paddle_build_endTime'] -
                                basic_ci_index_dict['paddle_build_startTime'])
                    log_filename = "buildLog/%s_%s_%s_cpu.log" % (
                        res['pipelineConfName'], self.sha, commit_createTime)
                    EXCODE = self.getExcode(res['pipelineConfName'],
                                            log_filename)
                else:
                    ##gputest 执行时间选耗时长的 等待时间选等待最长的？？合理吗？
                    gpu_waitTime = 0
                    gpu_execTime = 0
                    gpu_excode = []
                    if len(testScope) == 0:  ##只有编译任务，没有测试任务
                        log_filename = "buildLog/%s_%s_%s_cpu.log" % (
                            res['pipelineConfName'], self.sha,
                            commit_createTime)
                        EXCODE = self.getExcode(res['pipelineConfName'],
                                                log_filename)
                        waitTime_total = (
                            basic_ci_index_dict['clone_code_startTime'] -
                            commit_createTime
                        ) + (basic_ci_index_dict['docker_build_startTime'] -
                             basic_ci_index_dict['clone_code_endTime']) + (
                                 basic_ci_index_dict['paddle_build_startTime']
                                 - basic_ci_index_dict['docker_build_endTime'])
                        execTime_total = (
                            basic_ci_index_dict['clone_code_endTime'] -
                            basic_ci_index_dict['clone_code_startTime']
                        ) + (basic_ci_index_dict['docker_build_endTime'] -
                             basic_ci_index_dict['docker_build_startTime']) + (
                                 basic_ci_index_dict['paddle_build_endTime'] -
                                 basic_ci_index_dict['paddle_build_startTime'])
                    else:
                        for test in testScope:
                            test = test.replace('-', '_')
                            gpu_waitTime_tem = basic_ci_index_dict[
                                '%s_startTime' % test] - basic_ci_index_dict[
                                    'paddle_build_endTime']
                            if gpu_waitTime_tem > gpu_waitTime:
                                gpu_waitTime = gpu_waitTime_tem
                            gpu_execTime_tem = basic_ci_index_dict[
                                '%s_endTime' %
                                test] - basic_ci_index_dict['%s_startTime' %
                                                            test]
                            if gpu_execTime_tem > gpu_execTime:
                                gpu_execTime = gpu_execTime_tem
                            log_filename = "buildLog/%s_%s_%s_%s_gpu.log" % (
                                res['pipelineConfName'], test.replace(
                                    '-', '_'), self.sha, commit_createTime)
                            if test == 'paddle_test' or len(testScope) == 1:
                                EXCODE = self.getExcode(
                                    res['pipelineConfName'], log_filename)
                            else:
                                if test.split('_')[1] == 'infer':
                                    EXCODE_infer = self.getExcode(
                                        res['pipelineConfName'], log_filename)
                                    basic_ci_index_dict[
                                        'EXCODE_infer'] = EXCODE_infer
                        waitTime_total = (
                            basic_ci_index_dict['clone_code_startTime'] -
                            commit_createTime) + (
                                basic_ci_index_dict['docker_build_startTime'] -
                                basic_ci_index_dict['clone_code_endTime']
                            ) + (basic_ci_index_dict['paddle_build_startTime']
                                 - basic_ci_index_dict['docker_build_endTime']
                                 ) + gpu_waitTime
                        execTime_total = (
                            basic_ci_index_dict['clone_code_endTime'] -
                            basic_ci_index_dict['clone_code_startTime']) + (
                                basic_ci_index_dict['docker_build_endTime'] -
                                basic_ci_index_dict['docker_build_startTime']
                            ) + (basic_ci_index_dict['paddle_build_endTime'] -
                                 basic_ci_index_dict['paddle_build_startTime']
                                 ) + gpu_execTime

            else:
                for stage in CIIndex:
                    for job in CIIndex[stage]:
                        if job == 'Git-clone':
                            clone_code_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'clone_code_startTime'] = CIIndex[stage][job][
                                    'startTime']
                            basic_ci_index_dict[
                                'clone_code_endTime'] = CIIndex[stage][job][
                                    'endTime']
                        elif job in ['构建镜像', 'build-docker-image']:
                            build_docker_status = CIIndex[stage][job]['status']
                            basic_ci_index_dict[
                                'docker_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'docker_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                        else:
                            paddle_build_status = CIIndex[stage][job]['status']
                            logUrl = CIIndex[stage][job]['logUrl']
                            basic_ci_index_dict[
                                'paddle_build_startTime'] = CIIndex[stage][
                                    job]['startTime']
                            basic_ci_index_dict[
                                'paddle_build_endTime'] = CIIndex[stage][job][
                                    'endTime']
                if self.repo not in ['PaddlePaddle/Paddle']:
                    waitTime_total = (
                        basic_ci_index_dict['docker_build_startTime'] -
                        commit_createTime
                    ) + (
                        basic_ci_index_dict['paddle_build_startTime'] -
                        basic_ci_index_dict['docker_build_endTime']
                    ) if build_docker_status == 'SUCC' else basic_ci_index_dict[
                        'docker_build_startTime'] - commit_createTime
                    execTime_total = (
                        basic_ci_index_dict['paddle_build_endTime'] -
                        basic_ci_index_dict['paddle_build_startTime']
                    ) + (
                        basic_ci_index_dict['docker_build_endTime'] -
                        basic_ci_index_dict['docker_build_startTime']
                    ) if build_docker_status == 'SUCC' else basic_ci_index_dict[
                        'docker_build_endTime'] - basic_ci_index_dict[
                            'docker_build_startTime']
                    EXCODE = 0 if paddle_build_status == 'SUCC' else 1
                else:
                    if logUrl != None:
                        self.getIpipeBuildLog(res['pipelineConfName'],
                                              commit_createTime, logUrl)
                    if clone_code_status == 'FAIL':
                        waitTime_total = basic_ci_index_dict[
                            'clone_code_startTime'] - commit_createTime
                        execTime_total = basic_ci_index_dict[
                            'clone_code_endTime'] - basic_ci_index_dict[
                                'clone_code_startTime']
                        EXCODE = self.EXCODE_DICT['clone_code_failed']
                    elif build_docker_status == 'FAIL':
                        waitTime_total = (
                            basic_ci_index_dict['clone_code_startTime'] -
                            commit_createTime) + (
                                basic_ci_index_dict['docker_build_startTime'] -
                                basic_ci_index_dict['clone_code_endTime'])
                        execTime_total = (
                            basic_ci_index_dict['clone_code_endTime'] -
                            basic_ci_index_dict['clone_code_startTime']) + (
                                basic_ci_index_dict['docker_build_endTime'] -
                                basic_ci_index_dict['docker_build_startTime'])
                        EXCODE = self.EXCODE_DICT['docker_build_failed']
                    else:
                        waitTime_total = (
                            basic_ci_index_dict['clone_code_startTime'] -
                            commit_createTime
                        ) + (
                            basic_ci_index_dict['docker_build_startTime'] -
                            basic_ci_index_dict['clone_code_endTime']
                        ) + (
                            basic_ci_index_dict['paddle_build_startTime'] -
                            basic_ci_index_dict['docker_build_endTime']
                        ) if 'clone_code_startTime' in basic_ci_index_dict else (
                            basic_ci_index_dict['docker_build_startTime'] -
                            commit_createTime) + (
                                basic_ci_index_dict['paddle_build_startTime'] -
                                basic_ci_index_dict['docker_build_endTime'])
                        execTime_total = (
                            basic_ci_index_dict['paddle_build_endTime'] -
                            basic_ci_index_dict['paddle_build_startTime']
                        ) + (
                            basic_ci_index_dict['docker_build_endTime'] -
                            basic_ci_index_dict['docker_build_startTime']
                        ) + (
                            basic_ci_index_dict['clone_code_endTime'] -
                            basic_ci_index_dict['clone_code_startTime']
                        ) if 'clone_code_startTime' in basic_ci_index_dict else (
                            basic_ci_index_dict['docker_build_endTime'] -
                            basic_ci_index_dict['docker_build_startTime']) + (
                                basic_ci_index_dict['paddle_build_endTime'] -
                                basic_ci_index_dict['paddle_build_startTime'])
                        log_filename = "buildLog/%s_%s_%s.log" % (
                            res['pipelineConfName'], self.sha,
                            commit_createTime)
                        EXCODE = self.getExcode(res['pipelineConfName'],
                                                log_filename)
            basic_ci_index_dict['EXCODE'] = EXCODE
            basic_ci_index_dict['waitTime_total'] = waitTime_total
            basic_ci_index_dict['execTime_total'] = execTime_total
            logger.info("basic_ci_index_dict: %s" % basic_ci_index_dict)
            return basic_ci_index_dict

    def getExcode(self, pipelineConfName, log_filename):
        """获取退出码"""
        f = open('%s' % log_filename, 'r')
        data = f.read()
        try:
            if '自动合并失败，修正冲突然后提交修正的结果。' in data or 'Automatic merge failed; fix conflicts and then commit the result.' in data:
                EXCODE = self.EXCODE_DICT['code_conflict']
            elif 'Received HTTP code 503 from proxy after CONNECT' in data or 'Failed to connect to' in data:
                EXCODE = self.EXCODE_DICT['http_proxy_failed']
            elif 'fatal: refusing to merge unrelated histories' in data:
                EXCODE = self.EXCODE_DICT['code_too_old']
            elif pipelineConfName.startswith(
                    'PR-CI-APPROVAL') or pipelineConfName.startswith(
                        'PR-CI-Mac'):
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
        logger.info("%s_%s EXCODE = %s" % (pipelineConfName, self.sha, EXCODE))
        return EXCODE

    def getDetailsCIIndex(self, basic_ci_index):
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
        detailed_ci_index_dict['PR'] = int(basic_ci_index['PR'])
        detailed_ci_index_dict['EXCODE'] = EXCODE
        detailed_ci_index_dict['triggerUser'] = basic_ci_index['triggerUser']
        detailed_ci_index_dict['createTime'] = basic_ci_index[
            'commit_createTime']
        detailed_ci_index_dict['branch'] = basic_ci_index['branch']
        detailed_ci_index_dict['repo'] = basic_ci_index['repo']
        detailed_ci_index_dict['execTime_total'] = basic_ci_index[
            'execTime_total']
        detailed_ci_index_dict['waitTime_total'] = basic_ci_index[
            'waitTime_total']
        #detailed_ci_index_dict['endTime'] = basic_ci_index['paddle_build_endTime'] if 'paddle_build_endTime' in basic_ci_index else basic_ci_index['docker_build_endTime']
        detailed_ci_index_dict['documentfix'] = basic_ci_index['documentfix']

        analysis_ci_index = self.analyze_failed_cause(
            basic_ci_index)  #分析PR失败原因
        if ciName.startswith(
            ('PR-CI-APPROVAL', 'PR-CI-OP-benchmark',
             'PR-CI-Model-benchmark')) or EXCODE in [1, 2, 7, 64, 503]:
            pass
        else:
            ### buildTime/ccache/whlSize/buildSize
            if ciName.startswith(('PR-CI-Build')):
                filename = '%s_%s_%s_cpu.log' % (
                    ciName, commitId, basic_ci_index['commit_createTime'])
            elif ciName.startswith(self.Paddle_cpu_gpu_separate_ci_tuple):
                filename = '%s_%s_%s_cpu.log' % (
                    ciName, commitId, basic_ci_index['commit_createTime'])
            else:
                filename = '%s_%s_%s.log' % (
                    ciName, commitId, basic_ci_index['commit_createTime'])
            f = open('buildLog/%s' % filename, 'r')
            data = f.read()
            buildTime_strlist = data.split('Build Time:', 1)
            buildTime = buildTime_strlist[1:][0].split('s')[0].strip()
            detailed_ci_index_dict['buildTime'] = float(buildTime)
            #收集ccache
            if ciName in [
                    'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-CPU-Py2',
                    'PR-CI-Inference', 'PR-CI-Mac-Python3', 'PR-CI-Build'
            ]:
                ccacheRate_strlist = data.split('ccache hit rate:', 1)
                ccacheRate = ccacheRate_strlist[1:][0].split('%')[0].strip()
                detailed_ci_index_dict['ccacheRate'] = float(ccacheRate)
            if ciName in ['PR-CI-Windows']:
                ccacheRate_strlist = data.split(
                    'ipipe_log_param_sccache_Hit_Hate:', 1)
                ccacheRate = ccacheRate_strlist[1:][0].split('%')[0].strip()
                detailed_ci_index_dict['ccacheRate'] = float(ccacheRate)
            #infenece
            if filename.startswith('PR-CI-Inference'):
                fluidInferenceSize_strlist = data.split(
                    'Paddle_Inference Size:', 1)
                fluidInferenceSize = fluidInferenceSize_strlist[1:][0].split(
                    'M')[0].strip()
                fluidInferenceSize_so_strlist = data.split(
                    'ipipe_log_param_Paddle_Inference_So_Size:', 1)
                fluidInferenceSize_so = fluidInferenceSize_so_strlist[1:][
                    0].split('M')[0].strip()
                detailed_ci_index_dict['fluidInferenceSize_so'] = float(
                    fluidInferenceSize_so)
                f.close()
                filename = '%s_paddle_test_%s_%s_gpu.log' % (
                    ciName, commitId, basic_ci_index['commit_createTime'])
                f = open('buildLog/%s' % filename, 'r')
                data = f.read()
                detailed_ci_index_dict['fluidInferenceSize'] = float(
                    fluidInferenceSize)
                testFluidLibTime_strlist = data.split(
                    'infer_ut tests Total time:', 1)
                testFluidLibTime = testFluidLibTime_strlist[1:][0].split('s')[
                    0].strip()
                detailed_ci_index_dict['testFluidLibTime'] = float(
                    testFluidLibTime)

            #Mac
            elif filename.startswith('PR-CI-Mac-Python3'):
                testCaseTime_mac_strlist = data.split('Mac testCase Time:')
                testCaseTime_mac = int(testCaseTime_mac_strlist[1:][0].split(
                    's')[0].strip())
                detailed_ci_index_dict['testCaseTime_total'] = testCaseTime_mac

            # Coverage/Py3/CPU-Py2/PR-CI-Build
            elif filename.startswith(('PR-CI-Coverage', 'PR-CI-Build',
                                      'PR-CI-Py3', 'PR-CI-CPU-Py2')):
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

                #精准测试
                if filename.startswith(self.PRECISION_TEST_CI_tuple):
                    f.close()
                    filename = '%s_paddle_test_%s_%s_gpu.log' % (
                        ciName, commitId, basic_ci_index['commit_createTime'])
                    f = open('buildLog/%s' % filename, 'r')
                    data = f.read()
                    detailed_ci_index_dict[
                        'PRECISION_TEST'] = True if analysis_ci_index[
                            'PRECISION_TEST'] == 'true' else False
                    if detailed_ci_index_dict[
                            'PRECISION_TEST'] == 'true':  #命中精致测试 只拿testCaseTime_total
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
                        testCaseTime_multi = 0
                        for item in testCaseTime_multi_strlist[1:]:
                            testCaseTime_multi += int(
                                item.split('s')[0].strip())
                        detailed_ci_index_dict[
                            'testCaseTime_multi'] = testCaseTime_multi
                        testCaseTime_exclusive_strlist = data.split(
                            'exclusive TestCases Total Time:')
                        testCaseTime_exclusive = 0
                        for item in testCaseTime_exclusive_strlist[1:]:
                            testCaseTime_exclusive += int(
                                item.split('s')[0].strip())
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

            elif filename.startswith(
                    'PR-CI-Windows') and not filename.startswith(
                        'PR-CI-Windows-OPENBLAS'):
                detailed_ci_index_dict[
                    'PRECISION_TEST'] = True if analysis_ci_index[
                        'PRECISION_TEST'] == 'true' else False
                #fluidInferenceSize_strlist = data.split('Windows Paddle_Inference Size:', 1)
                #fluidInferenceSize = fluidInferenceSize_strlist[1].split('M')[0].strip()
                #detailed_ci_index_dict['fluidInferenceSize'] = float(fluidInferenceSize)
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

                testCaseCount_single_strlist = data.split(
                    'Windows 1 card TestCases count is')
                testCaseCount_single = int(testCaseCount_single_strlist[-1]
                                           .split('\n')[0].strip())
                detailed_ci_index_dict[
                    'testCaseCount_single'] = testCaseCount_single
                testCaseCount_total = testCaseCount_single
                detailed_ci_index_dict[
                    'testCaseCount_total'] = testCaseCount_total

            f.close()
        return detailed_ci_index_dict

    def analyze_failed_cause(self, index_dict):
        analysis_ci_index = {}
        analysis_ci_index['PR'] = int(index_dict['PR'])
        analysis_ci_index['commitId'] = index_dict['commitId']
        analysis_ci_index['ciName'] = index_dict['ciName']
        analysis_ci_index['commit_createTime'] = index_dict[
            'commit_createTime']
        analysis_ci_index['execTime_total'] = index_dict['execTime_total']
        analysis_ci_index['waitTime_total'] = index_dict['waitTime_total']
        EXCODE = index_dict['EXCODE']
        analysis_ci_index['EXCODE'] = EXCODE
        analysis_ci_index['triggerUser'] = index_dict['triggerUser']
        analysis_ci_index['targetUrl'] = self.target_url
        if EXCODE == 0:
            isException = 0
            analysis_ci_index['description'] = 'document_fix' if index_dict[
                'documentfix'] == 'True' else 'success'
        elif EXCODE == self.EXCODE_DICT['clone_code_failed']:
            isException = 0
            analysis_ci_index['description'] = 'clone_code_failed'
        elif EXCODE == self.EXCODE_DICT['docker_build_failed']:
            isException = 0
            analysis_ci_index['description'] = 'docker_build_failed'
        elif EXCODE == self.EXCODE_DICT['temporary_files_failed']:
            isException = 0
            analysis_ci_index['description'] = 'pr has temporary files'
        elif EXCODE == self.EXCODE_DICT['code_conflict']:
            isException = 0
            analysis_ci_index['description'] = 'code conflict'
        elif EXCODE == self.EXCODE_DICT['code_style_failed']:
            isException = 0
            analysis_ci_index['description'] = 'code_style_failed'
        elif EXCODE == self.EXCODE_DICT['approve_failed']:
            isException = 0
            analysis_ci_index['description'] = 'pr need to approve'
        elif EXCODE == self.EXCODE_DICT['code_too_old']:
            isException = 0
            analysis_ci_index['description'] = 'code too old'
        elif EXCODE == self.EXCODE_DICT['http_proxy_failed']:
            isException = 1
            analysis_ci_index['description'] = 'HTTP PROXY NOT Good'
        elif EXCODE == self.EXCODE_DICT['build_failed']:
            query_stat = "SELECT EXCODE,PR,commitId FROM paddle_ci_index WHERE ciName='%s' order by time desc limit 5" % index_dict[
                'ciName']
            result = list(self.db.query(query_stat))
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
            if index_dict[
                    'ciName'].startswith(self.Paddle_cpu_gpu_separate_ci_tuple
                                         ) and '2' not in index_dict['ciName']:
                analysis_ci_index['cpu_waitTime'] = (
                    index_dict['docker_build_startTime'] -
                    index_dict['clone_code_endTime']) + (
                        index_dict['clone_code_startTime'] -
                        index_dict['commit_createTime'])
            analysis_ci_index['description'] = 'build_failed'
        elif EXCODE == self.EXCODE_DICT['test_failed'] and index_dict[
                'ciName'].startswith(
                    self.Paddle_testFailed_analysis_ci_tuple):  #单测失败原因
            isException = 0  # 先默认是PR本身的单测问题
            testsfailed_list = []
            WLIST_PR = wlist_alarm.wlist_pr
            WLIST_UT = wlist_alarm.wlist_ut
            shortcommitId = index_dict['commitId'][0:7]
            if index_dict['ciName'].startswith(
                    self.Paddle_cpu_gpu_separate_ci_tuple):
                filename = '%s_%s_%s_gpu.log' % (
                    index_dict['ciName'], index_dict['commitId'],
                    index_dict['commit_createTime'])
            else:
                filename = '%s_%s_%s.log' % (index_dict['ciName'],
                                             index_dict['commitId'],
                                             index_dict['commit_createTime'])
            f = open('buildLog/%s' % filename, 'r')
            data = f.read()
            if index_dict['ciName'].startswith('PR-CI-Windows') and index_dict[
                    'ciName'] != 'PR-CI-Windows-Remain-BuildTest':  #Mac/Windows
                testsfailed_strlist = data.split('The following tests FAILED:',
                                                 1)
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
            print(testsfailed_list)
            os.remove("buildLog/testsfailed_%s" % filename)
            if len(testsfailed_list) > 20:
                logger.error("PR's uts failed 20+: %s %s: %s" % (
                    index_dict['PR'], index_dict['ciName'], target_url))
                isException = 0
                analysis_ci_index['description'] = "PR's uts failed 20+"
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
                    self.create_failed_cause_csv(failed_cause_file)
                if os.path.exists(rerun_failed_cause_file) == False:
                    self.create_failed_cause_csv(rerun_failed_cause_file)
                for t in testsfailed_list:
                    df = pd.read_csv(failed_cause_file)
                    IFRERUN = False
                    failed_write_file = failed_cause_file
                    for index, row in df.iterrows():
                        if index_dict['PR'] == row[
                                'PR'] and shortcommitId == row[
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
                    write_data.to_csv(
                        failed_write_file, mode='a', header=False)
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
                    self.send_utfailed_mail(alarm_ut_dict_ult)
                    isException = 1  #必挂
                    analysis_ci_index['description'] = "ut failed certainly"
        elif EXCODE == self.EXCODE_DICT['coverage_failed']:
            if index_dict['ciName'].startswith(
                    self.Paddle_cpu_gpu_separate_ci_tuple):
                filename = '%s_%s_%s_gpu.log' % (
                    index_dict['ciName'], index_dict['commitId'],
                    index_dict['commit_createTime'])
            else:
                filename = '%s_%s_%s.log' % (index_dict['ciName'],
                                             index_dict['commitId'],
                                             index_dict['commit_createTime'])
            f = open('buildLog/%s' % filename, 'r')
            data = f.read()
            covfailed_strlist = data.split('expected >= 90.0 %, actual', 1)
            covRate = float(covfailed_strlist[1].split('%, failed')[0].strip())
            analysis_ci_index['covRate'] = covRate
            analysis_ci_index[
                'description'] = 'Coverage Rate NOT Reach The Standard'
            isException = 0
        else:
            isException = 0  #EXCODE==1时暂定为非异常
            analysis_ci_index['description'] = 'unkown failed'
            logger.info("unkown failed: %s" % analysis_ci_index)

        analysis_ci_index['isException'] = isException
        if index_dict['ciName'].startswith(self.SkipTestCi_tuple):
            isSkipTest = 0
            isSkipDir = 0
            filename = '%s_%s_%s.log' % (index_dict['ciName'],
                                         index_dict['commitId'],
                                         index_dict['commit_createTime'])
            f = open('buildLog/%s' % filename, 'r')
            data = f.read()
            if 'paddle whl does not diff in PR-CI-Model-benchmark, so skip this ci' in data:
                isSkipTest = 1
            if 'The modified files does not affect models in PR-CI-Model-benchmark, so skip this ci.' in data:
                isSkipDir = 1
            analysis_ci_index['isSkipTest'] = isSkipTest
            analysis_ci_index['isSkipDir'] = isSkipDir
        # 获取精准测试监控指标
        if index_dict['ciName'].startswith(
                self.PRECISION_TEST_CI_tuple) and EXCODE not in [
                    self.EXCODE_DICT['clone_code_failed'],
                    self.EXCODE_DICT['docker_build_failed'],
                    self.EXCODE_DICT['build_failed'],
                    self.EXCODE_DICT['http_proxy_failed'],
                    self.EXCODE_DICT['code_conflict'],
                    self.EXCODE_DICT['code_too_old']
                ]:
            PRECISION_TEST = None
            PRECISION_TEST_Cases_count = None
            PRECISION_TEST_Cases_ratio = None
            notHitMapFiles = None
            filterFiles = None
            hitMapFiles = None
            if index_dict['ciName'].startswith(
                    self.Paddle_cpu_gpu_separate_ci_tuple):
                filename = '%s_%s_%s_gpu.log' % (
                    index_dict['ciName'], index_dict['commitId'],
                    index_dict['commit_createTime'])
            else:
                filename = '%s_%s_%s.log' % (index_dict['ciName'],
                                             index_dict['commitId'],
                                             index_dict['commit_createTime'])
            f = open('buildLog/%s' % filename, 'r')
            data = f.read()
            if 'ipipe_log_param_PRECISION_TEST_Cases_count' in data:
                PRECISION_TEST_Cases_count = data.split(
                    'ipipe_log_param_PRECISION_TEST_Cases_count:', 1)
                PRECISION_TEST_Cases_count = int(PRECISION_TEST_Cases_count[1:]
                                                 [0].split('\n')[0].strip())
            if 'ipipe_log_param_PRECISION_TEST_Cases_ratio' in data:
                PRECISION_TEST_Cases_ratio = data.split(
                    'ipipe_log_param_PRECISION_TEST_Cases_ratio:', 1)
                PRECISION_TEST_Cases_ratio = round(
                    float(PRECISION_TEST_Cases_ratio[1:][0].split('\n')[0]
                          .strip()), 2)
            if 'notHitMapFiles' in data:
                notHitMapFiles = data.split('notHitMapFiles:', 1)
                notHitMapFiles = notHitMapFiles[1:][0].split('\n')[0].strip()
            if 'ipipe_log_param_PRECISION_TEST' in data:
                PRECISION_TEST = data.split('ipipe_log_param_PRECISION_TEST:',
                                            1)
                PRECISION_TEST = PRECISION_TEST[1:][0].split('\n')[0].strip()
            if 'filterFiles:' in data:
                filterFiles = data.split('filterFiles:', 1)
                filterFiles = filterFiles[1:][0].split('\n')[0].strip()
            if 'hitMapFiles:' in data:
                hitMapFiles = data.split('hitMapFiles:', 1)
                hitMapFiles = hitMapFiles[1:][0].split('\n')[0].strip()
            analysis_ci_index['PRECISION_TEST'] = PRECISION_TEST
            analysis_ci_index[
                'PRECISION_TEST_count'] = PRECISION_TEST_Cases_count
            analysis_ci_index[
                'PRECISION_TEST_ratio'] = PRECISION_TEST_Cases_ratio
            analysis_ci_index['PRECISION_TEST_notHitMapFiles'] = notHitMapFiles
            analysis_ci_index['PRECISION_TEST_hitMapFiles'] = hitMapFiles
            analysis_ci_index['PRECISION_TEST_filterFiles'] = filterFiles

        print(analysis_ci_index)
        result = self.db.insert('paddle_ci_analysis', analysis_ci_index)
        if result == True:
            logger.info('%s insert paddle_ci_analysis success!' %
                        analysis_ci_index)
        else:
            logger.info('%s insert paddle_ci_analysis failed!' %
                        analysis_ci_index)

    def create_failed_cause_csv(self, failed_cause_file):
        df = pd.DataFrame(columns=[
            'TIME', 'PR', 'COMMITID', 'CINAME', 'EXCODE', 'FAILED_MESSAGE',
            'ERROR_COUNT', 'CIURL'
        ])
        df.to_csv(failed_cause_file)

    def send_utfailed_mail(self, alarm_ut_dict):
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
            receiver = [
                'zhangchunle@baidu.com', 'tianshuo03@baidu.com',
                'xieyunshen@baidu.com', 'liuxudong04@baidu.com',
                'luotao02@baidu.com'
            ]
            title = '[告警] CI单测挂了三次以上！'
            sendMail(receiver, title, HTML_CONTENT)
