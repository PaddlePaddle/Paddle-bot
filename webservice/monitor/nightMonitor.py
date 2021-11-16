import json
import os
import time
import pandas as pd
import sys
sys.path.append("..")
from utils.resource import Resource
from utils.mail import Mail
from utils.handler import xlyHandler


class Monitor(xlyHandler):
    """正在运行任务监控"""

    def __init__(self):
        self.required_labels = [
            '广州-CPU集群', '保定-CPU集群', '保定-GPU-v100', '北京-GPU-V100',
            'Paddle-windows', 'Paddle-mac-py3', 'nTeslaV100-16', 'nTeslaP4'
        ]  #, 'Paddle-mac', 'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-cpu', 'Paddle-approval-cpu', 'Paddle-benchmark-P40', 'Paddle-Kunlun', 'Paddle-musl']
        self.Paddle_sa_cardType = [
            'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-cpu',
            'Paddle-approval-cpu', 'Paddle-benchmark-P40', 'Paddle-Kunlun',
            'Paddle-musl', 'Paddle-Sugon-DCU', 'Paddle-Ascend910-x86_64'
        ]
        self.labels_full_count = {
            '广州-CPU集群': 8,
            '保定-CPU集群': 12,
            '保定-GPU-v100': 15,
            '北京-GPU-V100': 10,
            'nTeslaP4': 5,
            'Paddle-windows': 14,
            'Paddle-mac-py3': 5,
            'nTeslaV100-16': 3
        }

    def getRunningJob(self):
        """
        this function will get all running list. Include containerJob and SaJob.
        Returns:
            
        """
        running_job_dict = {}
        #cpu-gpu分离的任务
        xly_container_running_task_list = self.getJobList('cpu_gpu_running')
        for task in xly_container_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] not in running_job_dict:
                running_job_dict[task['label']] = []
            running_job_dict[task['label']].append(task)

        #V100/P4 旧集群
        xly_container_running_task_list = self.getJobList('running')
        for task in xly_container_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] not in running_job_dict:
                running_job_dict[task['label']] = []
            running_job_dict[task['label']].append(task)

        #SA机器
        xly_sa_running_task_list = self.getJobList('sarunning')
        for task in xly_sa_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] not in running_job_dict:
                running_job_dict[task['label']] = []
            running_job_dict[task['label']].append(task)

        return running_job_dict

    def monitor(self):
        running_job_dict = self.getRunningJob()
        filename = '../buildLog/runningJobMonitor.csv'
        if os.path.exists(filename) == False:
            self.create_runningJob_monitor_csv(filename)
        for label in running_job_dict:
            if label in self.required_labels:
                running_job_size = len(running_job_dict[label])
                for task in running_job_dict[label]:
                    target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' % (
                        task['bid'], task['jobId'])
                    data = {
                        'TIME':
                        time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                        'cardType': label,
                        'running_job_size': running_job_size,
                        'runningJob': [task['name']],
                        'target_url': target_url,
                        'runningTime': task['running']
                    }
                    write_data = pd.DataFrame(data)
                    write_data.to_csv(filename, mode='a', header=False)

        filename = '../buildLog/resourcemonitor.csv'
        if os.path.exists(filename) == False:
            self.create_resource_monitor_csv(filename, 'runningJob')

        with open("../buildLog/wait_task.json", 'r') as load_f:
            all_waiting_task = json.load(load_f)
            load_f.close()

        waitting_job_list = {}
        for task in all_waiting_task:
            if task['label'] in self.required_labels:
                if task['label'] not in waitting_job_list:
                    waitting_job_list[task['label']] = []
                waitting_job_list[task['label']].append(task)

        for key in self.required_labels:
            if key not in all_waiting_task:
                waitting_job_list[key] = []

        idle_machineSize = {}
        for label in running_job_dict:
            if label in self.required_labels:
                idle_machineSize[label] = self.labels_full_count[label] - len(
                    running_job_dict[label])

        for label in waitting_job_list:
            data = {
                'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()),
                'cardType': label,
                'waittingJobSize': [len(waitting_job_list[label])],
                'IdleMachineSize': idle_machineSize[label]
            }
            write_data = pd.DataFrame(data)
            write_data.to_csv(filename, mode='a', header=False)

    def create_monitor_csv(self, filename, fileType):
        if fileType == 'runningJob':
            df = pd.DataFrame(columns=[
                'TIME', 'cardType', 'running_job_size', 'runningJob',
                'target_url', 'runningTime'
            ])
        elif fileType == 'resource':
            df = pd.DataFrame(columns=[
                'TIME', 'cardType', 'runningJobSize', 'waittingJobSize',
                'IdleMachineSize'
            ])
        df.to_csv(filename)


Monitor().monitor()
