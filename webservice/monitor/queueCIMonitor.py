import time
import requests
import json
import sys
sys.path.append("..")
from utils.db import Database


def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count


def queryDBlastHour(ci):
    endTime = int(time.time())
    startTime = endTime - 3600 * 2
    execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName='%s' and documentfix='False' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
        ci, startTime, endTime)
    execTime_last1hour = queryDB(execTime_last1hour_query_stat, 'mean')
    if execTime_last1hour == None:
        lastday = endTime - 3600 * 24
        execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName='%s' and documentfix='False' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, lastday, endTime)
        execTime_last1hour = queryDB(execTime_last1hour_query_stat, 'mean')
    execTime_last1hour = int(execTime_last1hour)
    return execTime_last1hour


def getJobList(url, jobStatus):
    V100_task_list = []
    P4_task_list = []
    response = requests.get(url).json()['news']
    for t in response:
        #if t['jobname'] != 'PADDLE_DOCKER_BUILD': #需不需要把构建镜像去掉？
        task = {}
        task['CIName'] = t['name']
        task[jobStatus] = t[jobStatus] if t[jobStatus] != None else 0
        task['PR'] = str(t['prid'])
        task['commitId'] = t['commit']
        task['targetId'] = t['bid']
        if jobStatus == 'running':
            task['jobname'] = t['jobname']
        if t['name'].startswith('PR-CI-Py35') or t['name'].startswith(
                'PR-CI-Coverage'):
            V100_task_list.append(task)
        elif t['name'].startswith('PR-CI-CPU-Py2') or t['name'].startswith(
                'PR-CI-Inference'):
            P4_task_list.append(task)
    return V100_task_list, P4_task_list


def runningCI(execTime_dict):
    url = 'http://xxxxxx/redmine/projects.json?key=running'
    V100_running_task, P4_running_task = getJobList(url,
                                                    'running')  #只是从api拿到的数据
    V100_running_task_list = []  #增加stillneedTime参数
    P4_running_task_list = []
    for task in V100_running_task:
        if task['CIName'].startswith('PR-CI-Coverage'):
            stillneedTime = execTime_dict['PR-CI-Coverage'] - task['running']
        elif task['CIName'].startswith('PR-CI-Py35'):
            stillneedTime = execTime_dict['PR-CI-Py35'] - task['running']
        if stillneedTime <= 0:
            stillneedTime = 10  #如果已经超过平均时间，统一认为还需要10min
        task['stillneedTime'] = stillneedTime
        V100_running_task_list.append(task)
    for task in P4_running_task:
        if task['CIName'].startswith('PR-CI-CPU-Py2'):
            stillneedTime = execTime_dict['PR-CI-CPU-Py2'] - task['running']
        elif task['CIName'].startswith('PR-CI-Inference'):
            stillneedTime = execTime_dict['PR-CI-Inference'] - task['running']
        if stillneedTime <= 0:
            stillneedTime = 10  #如果已经超过平均时间，统一认为还需要10min
        task['stillneedTime'] = stillneedTime
        P4_running_task_list.append(task)
    V100_running_task_list = sortTime(
        V100_running_task_list, 'stillneedTime', reverse=False)  #按时间正序
    P4_running_task_list = sortTime(
        P4_running_task_list, 'stillneedTime', reverse=False)

    all_running_task = V100_running_task_list + P4_running_task_list
    all_running_task = sortTime(
        all_running_task, 'stillneedTime', reverse=False)
    with open("../buildLog/running_task.json", "w") as f:
        json.dump(all_running_task, f)
        f.close()
    return V100_running_task_list, P4_running_task_list


def queueUpCI():
    url = 'http://xxxxxx/redmine/projects.json?key=waiting'
    V100_waiting_task, P4_waiting_task = getJobList(url,
                                                    'waiting')  #只是从api拿到的数据
    V100_waiting_task = sortTime(V100_waiting_task, 'waiting')  #按等待时间排序
    V100_waiting_task = forward18Task(V100_waiting_task)  #提前release18分支
    P4_waiting_task = sortTime(P4_waiting_task, 'waiting')
    P4_waiting_task = forward18Task(P4_waiting_task)  #提前release18分支

    execTime_dict = {}
    execTime_dict['PR-CI-Coverage'] = queryDBlastHour('PR-CI-Coverage')
    execTime_dict['PR-CI-Py35'] = queryDBlastHour('PR-CI-Py35')
    execTime_dict['PR-CI-CPU-Py2'] = queryDBlastHour('PR-CI-CPU-Py2')
    execTime_dict['PR-CI-Inference'] = queryDBlastHour('PR-CI-Inference')
    V100_running_task, P4_running_task = runningCI(execTime_dict)  #正在运行的任务

    #V100任务
    lastTaskToStartTime = 0
    for j in range(len(V100_waiting_task)):
        next_running_job = {}
        for key in V100_waiting_task[j]:
            next_running_job[key] = V100_waiting_task[j][key]
        if next_running_job['CIName'].startswith('PR-CI-Py35'):
            next_running_job['stillneedTime'] = execTime_dict['PR-CI-Py35']
        elif next_running_job['CIName'].startswith('PR-CI-Coverage'):
            next_running_job['stillneedTime'] = execTime_dict['PR-CI-Coverage']
        V100_waiting_task[j]['timeToStart'] = V100_running_task[0][
            'stillneedTime'] + lastTaskToStartTime
        lastTaskToStartTime = lastTaskToStartTime + V100_running_task[0][
            'stillneedTime']
        for i in range(1, len(V100_running_task)):
            new_stillneedTime = V100_running_task[i][
                'stillneedTime'] - V100_running_task[0]['stillneedTime']
            V100_running_task[i]['stillneedTime'] = new_stillneedTime
        del (V100_running_task[0])
        V100_running_task.append(next_running_job)
        V100_running_task = sortTime(
            V100_running_task, 'stillneedTime', reverse=False)

    #P4任务
    lastTaskToStartTime = 0
    for j in range(len(P4_waiting_task)):
        next_running_job = {}
        for key in P4_waiting_task[j]:
            next_running_job[key] = P4_waiting_task[j][key]
        if next_running_job['CIName'].startswith('PR-CI-CPU-Py2'):
            next_running_job['stillneedTime'] = execTime_dict['PR-CI-CPU-Py2']
        elif next_running_job['CIName'].startswith('PR-CI-Inference'):
            next_running_job['stillneedTime'] = execTime_dict[
                'PR-CI-Inference']
        P4_waiting_task[j]['timeToStart'] = P4_running_task[0][
            'stillneedTime'] + lastTaskToStartTime
        lastTaskToStartTime = lastTaskToStartTime + P4_running_task[0][
            'stillneedTime']
        for i in range(1, len(P4_running_task)):
            new_stillneedTime = P4_running_task[i][
                'stillneedTime'] - P4_running_task[0]['stillneedTime']
            P4_running_task[i]['stillneedTime'] = new_stillneedTime
        del (P4_running_task[0])
        P4_running_task.append(next_running_job)
        P4_running_task = sortTime(
            P4_running_task, 'stillneedTime', reverse=False)

    all_wait_task = V100_waiting_task + P4_waiting_task
    all_wait_task = sortTime(all_wait_task, 'timeToStart', reverse=False)
    with open("../buildLog/wait_task.json", "w") as f:
        json.dump(all_wait_task, f)
        f.close()


def sortTime(task_list, key, reverse=True):
    if len(task_list) != 0:
        task_list = sorted(
            task_list, key=lambda e: e.__getitem__(key), reverse=reverse)
    return task_list


def forward18Task(task_list):
    task_18 = []
    for task in task_list:
        if '-18' in task['CIName']:
            task_18.append(task)
            task_list.remove(task)
    task_list_new = task_18 + task_list
    return task_list_new


queueUpCI()
