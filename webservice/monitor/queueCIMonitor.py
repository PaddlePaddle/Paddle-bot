import time
import requests
import json
import sys
sys.path.append("..")
from utils.readConfig import ReadConfig

localConfig = ReadConfig('../conf/config.ini')


def getJobList(url, jobStatus, CItype='container'):
    ALL_TASK = []
    response = requests.get(url).json()['news']
    for t in response:
        task = {}
        task['repo'] = t['reponame']
        task['CIName'] = t['name']
        task[jobStatus] = t[jobStatus] if t[jobStatus] != None else 0
        task['PR'] = str(t['prid'])
        task['commitId'] = t['commit']
        task['targetId'] = t['bid']
        if t['reponame'] in ['PaddlePaddle/Paddle']:  #Paddle repo才需要判断
            task['ifDocument'] = ifDocument(t['commit'], t['reponame'])
        else:
            task['ifDocument'] = False
        if CItype == 'container':
            task['cardType'] = t['label']
        if jobStatus == 'running' and CItype == 'container':
            task['jobname'] = t['jobname']
        ALL_TASK.append(task)
    return ALL_TASK


def ifDocument(commit, repo):
    """判断是否指修改文档"""
    ifDocument = False
    url = 'https://api.github.com/repos/%s/commits/%s' % (repo, commit)
    response = requests.get(url).json()
    message = response['commit']['message']
    if 'test=document_fix' in message:
        ifDocument = True
    return ifDocument


def classify_container_task(container_task):
    """按卡区分"""
    V100_task_list = []  #coverage/py3
    P4_task_list = []  #cpu/inference/fluiddoc
    for t in container_task:
        if t['cardType'].startswith('nTeslaV100'):
            if t['repo'] in ['PaddlePaddle/Paddle', 'PaddlePaddle/FluidDoc']:
                V100_task_list.append(t)
            else:
                print('V100 OTHER repo Task: %s' % t)
        elif t['cardType'].startswith('nTeslaP4'):
            if t['repo'] in [
                    'PaddlePaddle/Paddle', 'PaddlePaddle/FluidDoc',
                    'PaddlePaddle/benchmark'
            ]:
                P4_task_list.append(t)
        else:
            print('OTHER CARD: %s' % t['cardType'])
    return V100_task_list, P4_task_list


def classify_sa_task(sa_task):
    """按任务名区分"""
    Mac_task_list = []  #mac/mac-python3
    Win_task_list = []  #win/win-openblas
    Benchmark_task_list = []  # benchmark
    Approval_task_list = []  #benchmark approval/paddle approval
    Kunlun_tak = []  #kunlun
    for t in sa_task:
        if 'Windows' in t['CIName']:
            Win_task_list.append(t)
        elif 'Mac' in t['CIName']:
            Mac_task_list.append(t)
        elif 'Benchmark' in t['CIName']:
            Benchmark_task_list.append(t)
        elif 'APPROVAL' in t['CIName']:
            Approval_task_list.append(t)
        else:
            print('OTHER task: %s' % t)
    return Mac_task_list, Win_task_list, Benchmark_task_list, Approval_task_list


def addStillneedTime(task_list, ci_list, execTime_dict):
    running_task_list = []
    for task in task_list:
        for ci in ci_list:
            if task['CIName'].startswith(
                    'PR-CI-Windows-OPENBLAS') and ci == 'PR-CI-Windows':
                break
            if task['CIName'].startswith(
                    'PR-CI-Mac-Python3') and ci == 'PR-CI-Mac':
                break
            key = '%s_%s_%s' % (ci, task['repo'], task['ifDocument'])
            if task['CIName'].startswith(ci):
                stillneedTime = execTime_dict[key] - task['running']
                if stillneedTime <= 0:
                    stillneedTime = 10  #如果已经超过平均时间，统一认为还需要10min
                task['stillneedTime'] = stillneedTime
                running_task_list.append(task)
    return running_task_list


def runningCI(execTime_dict):
    ALL_RUNNING_TAKS_DICT = {}
    url = 'http://10.138.37.228/redmine/projects.json?key=running'
    url_sa = 'http://10.138.37.228/redmine/projects.json?key=sarunning'
    container_task = getJobList(url, 'running')
    sa_task = getJobList(url_sa, 'running', 'sa')

    V100_task_list, P4_task_list = classify_container_task(container_task)
    Mac_task_list, Win_task_list, Benchmark_task_list, Approval_task_list = classify_sa_task(
        sa_task)

    V100_running_task_list = addStillneedTime(
        V100_task_list, ['PR-CI-Coverage', 'PR-CI-Py3'], execTime_dict)

    P4_running_task_list = addStillneedTime(
        P4_task_list, ['PR-CI-CPU-Py2', 'PR-CI-Inference'], execTime_dict)
    Mac_running_task_list = addStillneedTime(
        Mac_task_list, ['PR-CI-Mac-Python3', 'PR-CI-Mac'], execTime_dict)
    Win_running_task_list = addStillneedTime(
        Win_task_list, ['PR-CI-Windows-OPENBLAS', 'PR-CI-Windows'],
        execTime_dict)
    Benchmark_running_task_list = addStillneedTime(
        Benchmark_task_list, ['PR-CI-OP-Benchmark'], execTime_dict)
    Approval_running_task_list = addStillneedTime(
        Approval_task_list, ['PR-CI-APPROVAL'], execTime_dict)

    V100_running_task_list = sortTime(
        V100_running_task_list, 'stillneedTime', reverse=False)  #按时间正序
    ALL_RUNNING_TAKS_DICT['V100'] = V100_running_task_list
    P4_running_task_list = sortTime(
        P4_running_task_list, 'stillneedTime', reverse=False)
    ALL_RUNNING_TAKS_DICT['P4'] = P4_running_task_list
    Mac_running_task_list = sortTime(
        Mac_running_task_list, 'stillneedTime', reverse=False)
    ALL_RUNNING_TAKS_DICT['MAC'] = Mac_running_task_list
    Win_running_task_list = sortTime(
        Win_running_task_list, 'stillneedTime', reverse=False)
    ALL_RUNNING_TAKS_DICT['WIN'] = Win_running_task_list
    Benchmark_running_task_list = sortTime(
        Benchmark_running_task_list, 'stillneedTime', reverse=False)
    ALL_RUNNING_TAKS_DICT['BENCHMARK'] = Benchmark_running_task_list
    Approval_running_task_list = sortTime(
        Approval_running_task_list, 'stillneedTime', reverse=False)
    ALL_RUNNING_TAKS_DICT['APPROVAL'] = Approval_running_task_list

    all_running_task = V100_running_task_list + P4_running_task_list + Mac_running_task_list + Win_running_task_list + Benchmark_running_task_list + Approval_running_task_list
    all_running_task = sortTime(
        all_running_task, 'stillneedTime', reverse=False)
    with open("../buildLog/running_task.json", "w") as f:
        json.dump(all_running_task, f)
        f.close()
    return ALL_RUNNING_TAKS_DICT


def queueUpCI():
    url = 'http://10.138.37.228/redmine/projects.json?key=waiting'
    url_sa = 'http://10.138.37.228/redmine/projects.json?key=sawaiting'
    container_waiting_task = getJobList(url, 'waiting')  #只是从api拿到的数据
    sa_waiting_task = getJobList(url_sa, 'waiting', 'sa')
    V100_waiting_task, P4_waiting_task = classify_container_task(
        container_waiting_task)
    Mac_waiting_task, Win_waiting_task, Benchmark_waiting_task, Approval_waiting_task = classify_sa_task(
        sa_waiting_task)

    V100_waiting_task = sortTime(V100_waiting_task, 'waiting')  #按等待时间排序
    V100_waiting_task = forward18Task(V100_waiting_task)  #提前release分支
    P4_waiting_task = sortTime(P4_waiting_task, 'waiting')
    P4_waiting_task = forward18Task(P4_waiting_task)  #提前release分支s
    Mac_waiting_task = sortTime(Mac_waiting_task, 'waiting')  #按等待时间排序
    Mac_waiting_task = forward18Task(Mac_waiting_task)  #提前release分支
    Win_waiting_task = sortTime(Win_waiting_task, 'waiting')  #按等待时间排序
    Win_waiting_task = forward18Task(Win_waiting_task)  #提前release分支
    Benchmark_waiting_task = sortTime(Benchmark_waiting_task,
                                      'waiting')  #按等待时间排序
    Benchmark_waiting_task = forward18Task(
        Benchmark_waiting_task)  #提前release分支
    Approval_waiting_task = sortTime(Approval_waiting_task,
                                     'waiting')  #按等待时间排序
    Approval_waiting_task = forward18Task(Approval_waiting_task)  #提前release分支

    with open("../buildLog/all_ci_execTime.json",
              'r') as load_f:  #ci任务的时间存在all_ci_execTime.jso中
        execTime_dict = json.load(load_f)
        load_f.close()

    ALL_RUNNING_TAKS_DICT = runningCI(execTime_dict)

    V100_running_task_list = ALL_RUNNING_TAKS_DICT['V100']
    P4_running_task_list = ALL_RUNNING_TAKS_DICT['P4']
    Mac_running_task_list = ALL_RUNNING_TAKS_DICT['MAC']
    Win_running_task_list = ALL_RUNNING_TAKS_DICT['WIN']
    Benchmark_running_task_list = ALL_RUNNING_TAKS_DICT['BENCHMARK']
    Approval_running_task_list = ALL_RUNNING_TAKS_DICT['APPROVAL']

    V100_waiting_task = getQueueTaskTimeToStart(
        V100_waiting_task, V100_running_task_list,
        ['PR-CI-Coverage', 'PR-CI-Py3'], execTime_dict)
    P4_waiting_task = getQueueTaskTimeToStart(
        P4_waiting_task, P4_running_task_list,
        ['PR-CI-CPU-Py2', 'PR-CI-Inference', 'FluidDoc1', 'build-paddle'],
        execTime_dict)
    Mac_waiting_task = getQueueTaskTimeToStart(
        Mac_waiting_task, Mac_running_task_list,
        ['PR-CI-Mac-Python3', 'PR-CI-Mac'], execTime_dict)
    Win_waiting_task = getQueueTaskTimeToStart(
        Win_waiting_task, Win_running_task_list,
        ['PR-CI-Windows-OPENBLAS', 'PR-CI-Windows'], execTime_dict)
    Benchmark_waiting_task = getQueueTaskTimeToStart(
        Benchmark_waiting_task, Benchmark_running_task_list,
        ['PR-CI-OP-Benchmark'], execTime_dict)
    Approval_waiting_task = getQueueTaskTimeToStart(
        Approval_waiting_task, Approval_running_task_list, ['PR-CI-APPROVAL'],
        execTime_dict)
    all_wait_task = V100_waiting_task + P4_waiting_task + Mac_waiting_task + Win_waiting_task + Benchmark_waiting_task + Approval_waiting_task
    all_wait_task = sortTime(all_wait_task, 'timeToStart', reverse=False)
    with open("../buildLog/wait_task.json", "w") as f:
        json.dump(all_wait_task, f)
        f.close()


def getQueueTaskTimeToStart(waiting_task, running_task, ci_list,
                            execTime_dict):
    if len(running_task) != 0:
        lastTaskToStartTime = 0
        for j in range(len(waiting_task)):
            next_running_job = {}
            for key in waiting_task[j]:
                next_running_job[key] = waiting_task[j][key]
            for ci in ci_list:
                key = '%s_%s_%s' % (ci, next_running_job['repo'],
                                    next_running_job['ifDocument'])
                if next_running_job['CIName'].startswith(ci):
                    next_running_job['stillneedTime'] = execTime_dict[key]
            waiting_task[j]['timeToStart'] = running_task[0][
                'stillneedTime'] + lastTaskToStartTime
            lastTaskToStartTime = lastTaskToStartTime + running_task[0][
                'stillneedTime']
            for i in range(1, len(running_task)):
                new_stillneedTime = running_task[i][
                    'stillneedTime'] - running_task[0]['stillneedTime']
                running_task[i]['stillneedTime'] = new_stillneedTime
            del (running_task[0])
            running_task.append(next_running_job)
            running_task = sortTime(
                running_task, 'stillneedTime', reverse=False)
    elif len(running_task) == 0 and len(waiting_task) != 0:
        waiting_task[0]['timeToStart'] = 1  #running队列没有 认为还有1min
    return waiting_task


def sortTime(task_list, key, reverse=True):
    if len(task_list) != 0:
        task_list = sorted(
            task_list, key=lambda e: e.__getitem__(key), reverse=reverse)
    return task_list


def forward18Task(task_list):
    task_18 = []
    for task in task_list:
        if '-18' in task['CIName'] or '-20' in task['CIName']:
            task_18.append(task)
            task_list.remove(task)
    task_list_new = task_18 + task_list
    return task_list_new


queueUpCI()
