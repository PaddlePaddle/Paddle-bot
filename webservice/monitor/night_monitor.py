import json
import os
import time
import pandas as pd
import sys
sys.path.append("..")
from utils.resource import Resource
from utils.mail import Mail


class ResourceMonitor(Resource):
    """异常排队作业"""
    def __init__(self):
        self.required_labels = ['nTeslaV100-16', 'nTeslaP4']#, 'Paddle-mac', 'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-cpu', 'Paddle-approval-cpu', 'Paddle-benchmark-P40', 'Paddle-Kunlun', 'Paddle-musl']


    def classifyTaskByCardType(self, task_list, cardType):
        """
        this function will classify container tasks. eg nTeslaV100, nTeslaP4
        Args:
            container_task_list(list): 
            cardType(str): gpu card type. 
        Returns:
            cardType_task_list: .
        """
        #print("cardType: %s" %cardType)
        task_list_by_card = []
        for task in task_list:
            if task['label'] == cardType:
                task_list_by_card.append(task)
        #print(len(task_list_by_card))
        return len(task_list_by_card)

    def getRunningJobSize(self):
        """
        this function will get size of running job list in different types.
        """
        running_job_size = {}
        xly_container_running_task_list = self.getJobList('running')
        for label in self.required_labels:
            running_job_size[label] = self.classifyTaskByCardType(xly_container_running_task_list, label)
        return running_job_size

    def monitor(self):
        running_job_size = self.getRunningJobSize()
        print("running_job_size: %s" %running_job_size)
        idle_machineSize = {'nTeslaV100-16': 16 - running_job_size['nTeslaV100-16'], 'nTeslaP4':4-running_job_size['nTeslaP4']}
        print("idle_machineSize: %s" %idle_machineSize)
        filename = '../buildLog/resourcemonitor.csv' 
        if os.path.exists(filename) == False :
            self.create_resource_monitor_csv(filename)
        with open("../buildLog/wait_task.json", 'r') as load_f:
            all_waiting_task = json.load(load_f)
            load_f.close()
        V100_waitting_job = []
        P4_waitting_job = []
        for task in all_waiting_task:
            if task['cardType'] == 'nTeslaV100-16':
                V100_waitting_job.append(task)
            elif task['cardType'] == 'nTeslaP4':
                P4_waitting_job.append(task)
        v100_data = {'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()), 'cardType': 'nTeslaV100-16',  'waittingJobSize': [len(V100_waitting_job)], 'IdleMachineSize': idle_machineSize['nTeslaV100-16']}
        print(v100_data)
        write_data = pd.DataFrame(v100_data)
        write_data.to_csv(filename, mode='a', header=False)
        P4_data = {'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()), 'cardType': 'nTeslaP4',  'waittingJobSize': [len(P4_waitting_job)], 'IdleMachineSize': idle_machineSize['nTeslaP4']}
        print(P4_data)
        write_data = pd.DataFrame(P4_data)
        write_data.to_csv(filename, mode='a', header=False)

    def create_resource_monitor_csv(self, filename):
        df = pd.DataFrame(columns=['TIME','cardType', 'runningJobSize', 'waittingJobSize', 'IdleMachineSize'])
        df.to_csv(filename)

ResourceMonitor().monitor()