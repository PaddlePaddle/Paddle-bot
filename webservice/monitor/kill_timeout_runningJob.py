import requests
import json
import sys
sys.path.append("..")
from utils.test_auth_ipipe import xlyOpenApiRequest
from utils.mail import Mail
from utils.getJob_xly import JobList
import os
import time
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    filename='../logs/killTimeoutJob.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class killTimeoutRunningJob(JobList):
    """取消超时任务"""

    def __init__(self):
        self.__container_cardType = ['nTeslaV100', 'nTeslaP4']
        self.__sa_cardType = [
            'win', 'mac', 'benchmark', 'cinn', 'approval', 'kunlun'
        ]
        self.__coverage_timeout_default = 180
        self.__py3_timeout_default = 120
        self.__win_timeout_default = 80
        self.__winopenblas_timeout_default = 180
        self.__p4_timeout_default = 60
        self.__mac_timeout_default = 60
        self.__approval_timeout_default = 15

    def ifDockerFile(self, repo, commit):
        """判断commit是否修改dockerfile"""
        ifdockerfile = False
        url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
        headers = {'authorization': "Basic xxxx="}
        response = requests.get(url, headers=headers).json()
        files = response['files']
        for f in files:
            if 'dockerfile' in f['filename'].lower():
                ifdockerfile = True
                break
        return ifdockerfile

    def filterDockerFile(self, timeout_running_job):
        """过滤修改dockerfile的文件"""
        new_timeout_running_job = []
        for task in timeout_running_job:
            ifdockerfile = self.ifDockerFile(task['repoName'],
                                             task['commitId'])
            if ifdockerfile == False:
                new_timeout_running_job.append(task)
            else:
                logger.info("Dockerfile: %s" % task)
        return new_timeout_running_job

    def create_failed_cause_csv(self, kill_file):
        """创建存储文件"""
        df = pd.DataFrame(columns=[
            'TIME', 'PR', 'COMMITID', 'CINAME', 'RUNNINGTIME', 'TASKURL'
        ])
        df.to_csv(kill_file)

    def save_cancel_job(self, data):
        """将kill的任务存到"""
        kill_file = '../buildLog/kill_timeout_runninng_job.csv'
        if os.path.exists(kill_file) == False:
            create_failed_cause_csv(kill_file)
        write_data = pd.DataFrame(data)
        write_data.to_csv(kill_file, mode='a', header=False)

    def filter_timeout_task(self):
        """
        返回：真正超时且要取消的任务列表, 仅告警但不取消的任务列表
        """
        container_running_job = self.getJobList('running',
                                                self.__container_cardType)
        sa_running_job = self.getJobList('sarunning', self.__sa_cardType)
        container_running_job = self.filterDockerFile(container_running_job)
        sa_running_job = self.filterDockerFile(sa_running_job)
        timeout_running_job = []
        alarm_running_job = []
        for task in container_running_job:
            if 'nTeslaP4' in task['cardType']:
                if task['running'] > self.__p4_timeout_default:
                    timeout_running_job.append(task)
            elif 'nTeslaV100' in task['cardType']:
                if task['CIName'].startswith('PR-CI-Py3'):
                    if task['running'] > self.__py3_timeout_default:
                        timeout_running_job.append(task)
                elif task['CIName'].startswith('PR-CI-Coverage'):
                    if task['running'] > self.__coverage_timeout_default:
                        timeout_running_job.append(task)
                else:
                    if task['running'] > 60:
                        alarm_running_job.append(task)
                        logger.info('%s has running %s' %
                                    (task['CIName'], task['running']))
            else:
                logger.info('Container has other card: %s. %s' %
                            (task['cardType'], task))

        for task in sa_running_job:
            if 'mac' in task['cardType']:
                if task['running'] > self.__mac_timeout_default:
                    timeout_running_job.append(task)
            elif 'win' in task['cardType']:
                if task['CIName'].startswith('PR-CI-Windows-OPENBLAS'):
                    if task['running'] > self.__winopenblas_timeout_default:
                        timeout_running_job.append(task)
                else:
                    if task['running'] > self.__win_timeout_default:
                        timeout_running_job.append(task)
            elif 'approval' in task['cardType']:
                if task['running'] > self.__approval_timeout_default:
                    timeout_running_job.append(task)
            else:
                if task['running'] > 60:
                    alarm_running_job.append(task)
                    logger.info('%s has running %s' %
                                (task['CIName'], task['running']))
        return timeout_running_job, alarm_running_job

    def cancelJob_sendMail(self):
        timeout_running_job, alarm_running_job = self.filter_timeout_task()
        mailContent = ''
        if len(timeout_running_job) > 0:
            mailContent += " <p>以下任务被判定为运行超时, 已自动取消，请排查超时原因！</p> <p>超时规则: Coverage超过180min, Py3超过120min, Inference/CPU 超过60min, Mac/Mac-python3 超过60min, Windows超过80min, Windows-OPENBLAS超过180min</p> <table border='1' align=center> <caption><font size='3'><b>自动取消运行中的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>repo</td><td bgcolor='#d0d0d0'>任务链接</td></tr>"
            for task in timeout_running_job:
                target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' % (
                    task['targetId'], task['jobId'])
                data = {
                    'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                    'PR': task['PR'],
                    'COMMITID': task['commitId'],
                    'CINAME': task['CIName'],
                    'RUNNINGTIME': [task['running']],
                    'TASKURL': target_url
                }
                self.save_cancel_job(data)
                cancel_url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/job-builds/%s/operation-requests' % task[
                    'jobId']
                DATA = {"type": "CANCEL"}
                json_str = json.dumps(DATA)
                res = xlyOpenApiRequest().post_method(cancel_url, json_str)
                if res.status_code == 200 or res.status_code == 201:
                    mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                        task['PR'], task['CIName'], task['running'],
                        task['repoName'], target_url)
            mailContent += "</table>"
        if len(alarm_running_job) > 0:
            mailContent += "<p>此外, 以下任务已经运行超过60min, 请查看任务是否卡住.</p>"
            mailContent += "<table border='1' align=center> <caption><font size='3'><b>任务已运行超过60min</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>repo</td><td bgcolor='#d0d0d0'>任务链接</td></tr>"
            for task in alarm_running_job:
                task_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' % (
                    task['targetId'], task['jobId'])
                mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    task['PR'], task['CIName'], task['running'],
                    task['repoName'], task_url)
            mailContent += "</table>"
        if mailContent != '':
            self.sendMail(mailContent)

    def sendMail(self, mailContent):
        HTML_CONTENT = "<html><body><p>Hi, ALL:</p>"
        HTML_CONTENT += mailContent
        HTML_CONTENT += "<p>如有问题，请联系张春乐.</p> <p>张春乐</p></body></html>"
        mail = Mail()
        mail.set_sender('xxxx@baidu.com')
        mail.set_receivers(['xxx@baidu.com'])
        mail.set_title('[告警]自动取消超时任务')
        mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
        mail.send()


killTimeoutRunningJob().cancelJob_sendMail()
