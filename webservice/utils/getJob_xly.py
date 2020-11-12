import requests
import sys
sys.path.append("..")
from utils.auth_ipipe import xlyOpenApiRequest


class JobList(object):
    """作业列表"""

    def ifDocument(self, commit, repo):
        """判断是否指修改文档"""
        ifDocument = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {'authorization': "token xxx"}
        response = requests.get(url, headers=headers).json()
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
        url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/paddle-api/status?key=%s' % jobStatus
        param = 'key=running' if jobStatus == 'running' else 'key=waiting'
        response = xlyOpenApiRequest().get_method(url, param).json()
        all_task_list = []
        for t in response:
            task = {}
            task['repoName'] = t['repoName']
            task['CIName'] = t['name']
            task[jobStatus] = t[jobStatus] if t[jobStatus] != None else 0
            task['PR'] = str(t['pid'])
            task['commitId'] = t['commit']
            task['targetId'] = t['bid']
            task['cardType'] = t['label']
            task['jobId'] = t['jobId']
            if t['repoName'] in [
                    'PaddlePaddle/Paddle'
            ]:  #Paddle repo need to check if Document_fix 
                task['ifDocument'] = self.ifDocument(t['commit'],
                                                     t['repoName'])
            else:
                task['ifDocument'] = False
            for cardType in cardType_list:
                if cardType.lower() in task['cardType'].lower():
                    all_task_list.append(task)
                    break
        return all_task_list
