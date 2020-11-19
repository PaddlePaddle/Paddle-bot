#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import sys
import time
sys.path.append("..")
from utils.auth_ipipe import xlyOpenApiRequest


class JobList(object):
    """作业列表"""

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


class jobHandler(JobList):
    """作业处理"""

    def ifDocument(self, commit, repo):
        """判断是否指修改文档"""
        ifDocument = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {
            'authorization': "token 4a9505f4f857e3affce287d50ff1f9a4ad8b843f"
        }
        response = requests.get(url, headers=headers).json()
        message = response['commit']['message']
        if 'test=document_fix' in message:
            ifDocument = True
        return ifDocument

    def ifDockerFile(self, repo, commit):
        """判断commit是否修改dockerfile"""
        ifdockerfile = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {
            'Authorization': "token 237e1564a262d660bf016c46e109dadec2434e94"
        }
        response = requests.get(url, headers=headers).json()
        files = response['files']
        for f in files:
            if 'dockerfile' in f['filename'].lower():
                print('dockerfile::')
                print(f['filename'])
                ifdockerfile = True
                break
        return ifdockerfile
