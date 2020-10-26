import requests
import json
import sys
sys.path.append("..")
from utils.auth_ipipe import Post_ipipe_auth
from utils.mail import Mail
import os
import time
import pandas as pd


def filterDockerFile(timeout_running_job):
    new_timeout_running_job = []
    for task in timeout_running_job:
        ifdockerfile = ifDockerFile(task['repo'], task['commitId'])
        if ifdockerfile == False:
            new_timeout_running_job.append(task)
        else:
            print("Dockerfile: %s" % task)
    return new_timeout_running_job


def ifDockerFile(repo, commit):
    ifdockerfile = False
    url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
    response = requests.get(url).json()
    files = response['files']
    for f in files:
        if 'dockerfile' in f['filename'].lower():
            ifdockerfile = True
            break
    return ifdockerfile


def getJobList(url, jobStatus, CItype='container'):
    V100_task_list = []
    P4_task_list = []
    Mac_task_list = []
    Win_task_list = []
    response = requests.get(url).json()['news']
    for t in response:
        task = {}
        task['CIName'] = t['name']
        task[jobStatus] = t[jobStatus] if t[jobStatus] != None else 0
        task['PR'] = str(t['prid'])
        task['commitId'] = t['commit']
        task['targetId'] = t['bid']
        task['jobId'] = t['jobid']
        task['repo'] = t['reponame']
        if jobStatus == 'running' and CItype == 'container':
            task['jobname'] = t['jobname']
        if t['name'].startswith('PR-CI-Py3') or t['name'].startswith(
                'PR-CI-Coverage'):
            V100_task_list.append(task)
        elif t['name'].startswith('PR-CI-CPU-Py2') or t['name'].startswith(
                'PR-CI-Inference'):
            P4_task_list.append(task)
        elif t['name'].startswith('PR-CI-Mac'):
            Mac_task_list.append(task)
        elif t['name'].startswith('PR-CI-Windows'):
            Win_task_list.append(task)
    if CItype == 'sa':
        return Mac_task_list, Win_task_list
    else:
        return V100_task_list, P4_task_list


def runningCI():
    url = 'http://10.10.10.10/projects.json?key=running'
    url_sa = 'http://10.10.10.10/projects..json?key=sarunning'
    Mac_running_task, Win_running_task = getJobList(url_sa, 'running', 'sa')
    V100_running_task, P4_running_task = getJobList(url,
                                                    'running')  #只是从api拿到的数据

    timeout_running_job = []
    for task in Win_running_task:
        if task['CIName'].startswith('PR-CI-Windows-OPENBLAS'):
            if task['running'] > 180:
                timeout_running_job.append(task)
        else:
            if task['running'] > 80:
                timeout_running_job.append(task)
    for task in Mac_running_task:
        if task['running'] > 60:
            timeout_running_job.append(task)
    for task in V100_running_task:
        if task['CIName'].startswith('PR-CI-Coverage'):
            if task['running'] > 180:
                timeout_running_job.append(task)
        else:
            if task['running'] > 120:
                timeout_running_job.append(task)
    for task in P4_running_task:
        if task['running'] > 60:
            timeout_running_job.append(task)
    return timeout_running_job


def kill_timeout_runninng_job():
    kill_file = '../buildLog/kill_timeout_runninng_job.csv'
    if os.path.exists(kill_file) == False:
        create_failed_cause_csv(kill_file)
    HTML_CONTENT = "<html><body><p>Hi, ALL:</p> <p>以下任务被判定为运行超时, 已自动取消，请排查超时原因！</p> <p>超时规则: Coverage超过180min, Py3超过120min, Inference/CPU 超过60min, Mac/Mac-python3 超过60min, Windows超过80min, Windows-OPENBLAS超过180min</p> <table border='1' align=center> <caption><font size='3'><b>自动取消运行中的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>任务链接</td></tr>"
    timeout_running_job = runningCI()
    new_timeout_running_job = filterDockerFile(timeout_running_job)

    DATA = {"type": "CANCEL"}
    json_str = json.dumps(DATA)
    if len(new_timeout_running_job) > 0:
        for task in new_timeout_running_job:
            task_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' % (
                task['targetId'], task['jobId'])
            data = {
                'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                'PR': task['PR'],
                'COMMITID': task['commitId'],
                'CINAME': task['CIName'],
                'RUNNINGTIME': [task['running']],
                'TASKURL': task_url
            }
            write_data = pd.DataFrame(data)
            write_data.to_csv(kill_file, mode='a', header=False)
            cancel_url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/job-builds/%s/operation-requests' % task[
                'jobId']
            session, req = Post_ipipe_auth(cancel_url, json_str)
            try:
                res = session.send(req)
            except Exception as e:
                print("Error: %s" % e)
            else:
                HTML_CONTENT += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    task['PR'], task['CIName'], task['running'], task_url)
        HTML_CONTENT += "</table><p>如有问题，请联系张春乐.</p> <p>张春乐</p></body></html>"
        mail = Mail()
        mail.set_sender('xx@baidu.com')
        mail.set_receivers(['xxxx@baidu.com'])
        mail.set_title('[告警]自动取消超时任务')
        mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
        mail.send()


def create_failed_cause_csv(kill_file):
    df = pd.DataFrame(columns=[
        'TIME', 'PR', 'COMMITID', 'CINAME', 'RUNNINGTIME', 'TASKURL'
    ])
    df.to_csv(kill_file)


kill_timeout_runninng_job()
