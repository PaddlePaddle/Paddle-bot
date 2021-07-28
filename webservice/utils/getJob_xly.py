#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import sys
import time
sys.path.append("..")
from utils.test_auth_ipipe import xlyOpenApiRequest

class JobList(object):
    """作业列表"""
    def ifDocument(self, commit, repo):
        """判断是否指修改文档"""
        ifDocument = False
        url = 'https://api.github.com/repos/%s/commits/%s' %(repo, commit)
        headers = {'authorization': "token 4a9505f4f857e3affce287d50ff1f9a4ad8b843f"}
        response = requests.get(url, headers = headers).json()
        message = response['commit']['message']
        if 'test=document_fix' in message:
            ifDocument = True
        return ifDocument

    def getJobList(self, jobStatus, cardType_list): 
        """
        this function will get all Container job list. eg.V100/P4 type jobs.
        Args:
            jobStatus(str): job status. running/waiting/sarunning/sawaiting.
            cardType_list(str): card type.
        Returns:
            all_task_list(list): all task list
        """
        url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/paddle-api/status?key=%s' %jobStatus
        param = 'key=%s' %jobStatus
        headers= {"Content-Type": "application/json", "IPIPE-UID": "Paddle-bot"}
        start = int(time.time())
        response = xlyOpenApiRequest().get_method(url, param, headers=headers).json()
        end = int(time.time())
        print('end-start: %s' %(end-start))
        print(response)
        all_task_list = []
        for t in response:
            print(t)
            task = {}
            task['repoName'] = t['repoName']
            task['CIName'] = t['name']
            if 'running' in jobStatus:
                task['running'] = t['running']
            else:
                task['waiting'] = t['waiting']
            task['PR'] = str(t['pid'])
            task['commitId'] = t['commit']
            task['targetId'] = t['bid']
            task['cardType'] = t['label']
            task['jobId'] = t['jobId']
            if t['repoName'] in ['PaddlePaddle/Paddle']: #Paddle repo need to check if Document_fix 
                task['ifDocument'] = self.ifDocument(t['commit'], t['repoName'])
            else:
                task['ifDocument'] = False
            for cardType in cardType_list:
                if cardType.lower() in task['cardType'].lower() and t['jobName'] not in ['构建镜像', 'build-docker-image']:
                    if task['repoName'] in ['PaddlePaddle/Paddle', 'PaddlePaddle/benchmark', 'PaddlePaddle/FluidDoc', 'PaddlePaddle/PaddleRec', 'PaddlePaddle/CINN', 'PaddlePaddle/Serving']:
                        all_task_list.append(task)  
                    else:
                        print('OTHER REPO: %s' %task)
                    break
        return all_task_list
     

#JobList().getJobList('sarunning', ['win', 'mac', 'cpu', 'benchmark', 'cinn', 'approval'])
#JobList().getJobList('running', ['v100', 'p4'])