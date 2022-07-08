#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import time
import json
import re
import sys
sys.path.append("..")
from utils.auth_ipipe import xlyOpenApiRequest
from utils.readConfig import ReadConfig


class xlyHandler(object):
    """xly Openapi 封装"""

    def getJobList(self, jobStatus):
        """
        this function will get all Container job list. eg.V100/P4 type jobs.
        Args:
            jobStatus(str): job status. running/waiting/sarunning/sawaiting.
            cardType_list(str): card type.
        Returns:
            all_task_list(list): all task list
        """
        url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/paddle-api/status?key=%s' % jobStatus
        print(url)
        param = 'key=%s' % jobStatus
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        start = int(time.time())
        response = xlyOpenApiRequest().get_method(
            url, param, headers=headers).json()
        end = int(time.time())
        return response

    def getStageMessge(self, targetId):
        """
        获取任务的stage 信息
        """
        localConfig = ReadConfig('../conf/config.ini')
        url = localConfig.cf.get('ipipeConf', 'stage_url') + str(targetId)
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        response = xlyOpenApiRequest().get_method(url, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            return None

    def getJobLog(self, filename, logUrl):
        """
        1. 获取log url
        2. 获取log 写入文件
        """
        try:
            r = requests.get(logUrl)
        except Exception as e:
            print("Error: %s" % e)
        else:
            with open("%s" % filename, "wb") as f:
                f.write(r.content)
                f.close
            print("%s" % filename)

    def cancelJob(self, jobId):
        """取消任务"""
        cancel_url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/job-builds/%s/operation-requests' % jobId
        DATA = {"type": "CANCEL"}
        json_str = json.dumps(DATA)
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        res = xlyOpenApiRequest().post_method(
            cancel_url, json_str, headers=headers)
        return res

    def rerunJob(self, triggerId):
        """重新构建"""
        rerun_url = 'https://xly.bce.baidu.com/open-api/ipipe/agile/pipeline/doRebuild?pipeTriggerId=%s' % triggerId
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        query_param = 'pipeTriggerId=%s' % triggerId
        res = xlyOpenApiRequest().get_method(
            rerun_url, param=query_param, headers=headers)
        return res

    def getAllResource(self):
        """PaddlePaddle下所有的SA资源"""
        url = 'https://xly.bce.baidu.com/open-api/sa_server/sa/open/api/rest/v2/labels/details?groupName=paddlepaddle'
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        query_param = 'groupName=paddlepaddle'
        res = xlyOpenApiRequest().get_method(
            url, param=query_param, headers=headers)
        return res

    def getConcurrenceByResourceId(self, labelid):
        """根据资源id获取当前并发数"""
        query_param = 'groupName=paddlepaddle&origin=SELF&labelId=%s' % labelid
        url = 'https://xly.bce.baidu.com/open-api/sa_server/sa/open/api/rest/v2/agents/details?%s' % query_param
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        res = xlyOpenApiRequest().get_method(
            url, param=query_param, headers=headers)
        return res

    def getCIindex(self, jobid):
        query_param = 'jobBuildId=%s' % jobid
        url = "https://xly.bce.baidu.com/open-api/ipipe/rest/v1/paddle-api/job-params?%s" % query_param
        print(url)
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        res = xlyOpenApiRequest().get_method(
            url, param=query_param, headers=headers)
        print(res.text)
        return res

    def getCIhistoryRecord(self, ciName):
        ci_conf_id_map = {
            "PR-CI-Build-Daily": 21864,
            "PR-CI-Coverage-compile-Daily": 22678
        }
        if ciName not in ci_conf_id_map:
            return
        pipelineId = ci_conf_id_map[ciName]
        query_param = '_limit=5&_offset=0&pipelineId=%s' % pipelineId
        url = "https://xly.bce.baidu.com/open-api/ipipe/rest/v3/pipeline-builds/all?%s" % query_param
        headers = {
            "Content-Type": "application/json",
            "IPIPE-UID": "Paddle-bot"
        }
        res = xlyOpenApiRequest().get_method(
            url, param=query_param, headers=headers)
        return res


class PRHandler(object):
    """PR/commit处理"""

    def ifDocumentByCommitId(self, commit, repo):
        """通过commitId 判断是否指修改文档"""
        ifDocument = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {'Authorization': "token xxx"}
        try:
            response = requests.get(url, headers=headers).json()
        except requests.exceptions.ConnectionError:
            ifDocument = False
            print('requests.exceptions.ConnectionError: %s' % url)
        else:
            message = response['commit']['message']
            if 'test=document_fix' in message:
                ifDocument = True
        return ifDocument

    def ifDocumentByCommitMessage(self, commitmessage):
        """通过commitMessage 判断是否指修改文档"""
        ifDocument = True if 'test=document_fix' in commitmessage else False
        return ifDocument

    def ifDockerFile(self, repo, commit):
        """判断commit是否修改dockerfile"""
        ifdockerfile = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {'Authorization': "token xxx"}
        try:
            response = requests.get(url, headers=headers).json()
        except requests.exceptions.ConnectionError:
            ifdockerfile = False
            print('requests.exceptions.ConnectionError: %s' % url)
        else:
            files = response['files']
            for f in files:
                if 'dockerfile' in f['filename'].lower():
                    print('dockerfile::')
                    print(f['filename'])
                    ifdockerfile = True
                    break
        return ifdockerfile
