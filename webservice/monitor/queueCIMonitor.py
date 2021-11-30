# coding=UTF-8
import time
import requests
import json
import sys
sys.path.append("..")
from utils.readConfig import ReadConfig
from utils.test_auth_ipipe import xlyOpenApiRequest
from utils.handler import PRHandler, xlyHandler
localConfig = ReadConfig('../conf/config.ini')


class getQueueUpCIList(xlyHandler, PRHandler):
    """The final displayed list of queuedCI"""

    def __init__(self):
        #Paddle/FluidDoc/benchmarks/PaddleRec/CINN/Serving
        self.required_labels = [
            '保定-GPU-v100', '广州-CPU集群', '保定-CPU集群', 'nTeslaP4', 'Paddle-mac',
            'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-cpu',
            'Paddle-approval-cpu', 'Paddle-benchmark-P40', 'Paddle-Kunlun',
            'Paddle-musl'
        ]
        self.known_repo = [
            'PaddlePaddle/Paddle', 'PaddlePaddle/benchmark',
            'PaddlePaddle/docs', 'PaddlePaddle/PaddleRec', 'PaddlePaddle/CINN',
            'PaddlePaddle/Serving'
        ]

        self.container_cardType = ['保定-GPU-v100', '广州-CPU集群', '保定-CPU集群']
        self.Paddle_sa_cardType = [
            'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-inference',
            'Paddle-windows-cpu', 'Paddle-approval-cpu',
            'Paddle-benchmark-P40', 'Paddle-Kunlun', 'Paddle-musl',
            'Paddle-Sugon-DCU', 'Paddle-Ascend910-x86_64'
        ]
        self.Paddle_container_ci = (
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-OP-benchmark',
            'PR-CI-Model-benchmark', 'PR-CE-Framework', 'PR-CI-Inference',
            'PR-CI-Static-Check', 'Get-fluidInferenceSize', 'PR-CI-GpuPS',
            'PR-CI-Build', 'PR-CI-CINN')
        self.Paddle_sa_ci = ('PR-CI-Windows', 'PR-CI-Windows-OPENBLAS',
                             'PR-CI-Mac-Python3', 'PR-CI-ROCM-Compile',
                             'PR-CI-musl', 'PR-CI-Kunlun', 'PR-CI-NPU',
                             'PR-CI-APPROVAL')

        self.other_container_ci = (
            'xly-PR-CI-PY36', 'xly-PR-CI-PY38', 'Docs-NEW',
            'CI-PaddleRec-Py38-LinuxUbuntu-Cuda102-ALL-D')

        self.resource_count = {"广州-CPU集群": 8}

        self.container_ci = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Static-Check',
            'PR-CI-Inference', 'xly-PR-CI-PY35', 'xly-PR-CI-PY27', 'FluidDoc1',
            'build-paddle', 'xly-PR-CI-PY2', 'xly-PR-CI-PY3',
            'PR-CI-CUDA9-CUDNN7', 'PaddleServing文档测试', 'PR-CI-OP-benchmark'
        ]
        self.sa_ci = [
            'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS', 'PR-CI-Mac',
            'PR-CI-Mac-Python3', 'PR-CI-APPROVAL', 'PR-CI-OP-Benchmark',
            'PR-CI-musl', 'PR-CI-Kunlun'
        ]

    def sortTime(self, task_list, key, reverse=True):
        if len(task_list) != 0:
            task_list = sorted(
                task_list, key=lambda e: e.__getitem__(key), reverse=reverse)
        return task_list

    def forwardReleaseBranchTask(self, task_list):
        task_relese = []
        for task in task_list:
            if '-18' in task['name'] or '-21' in task['name']:
                task_relese.append(task)
                task_list.remove(task)
        task_list_new = task_relese + task_list
        return task_list_new

    def getExecTime(self):
        """
        this function will get execution time of each ci.
        Returns:
            execTime_dict(dict): execution time of each ci
        """
        with open("../buildLog/all_ci_execTime.json",
                  'r') as load_f:  #ci任务的时间存在all_ci_execTime.json中
            execTime_dict = json.load(load_f)
            load_f.close()
        return execTime_dict

    def getRunningJob(self):
        """
        this function will get all running list. Include containerJob and SaJob.
        Returns:
            all_running_task_list: all running job list.
        """
        #cpu-gpu分离的任务
        xly_container_running_task_list = self.getJobList('cpu_gpu_running')
        gz_cpu_running_container = []
        bd_cpu_running_container = []
        bd_v100_running_container = []
        bj_v100_running_container = []
        for task in xly_container_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] == '广州-CPU集群':
                gz_cpu_running_container.append(task)
            elif task['label'] == '保定-CPU集群':
                bd_cpu_running_container.append(task)
            elif task['label'] == '保定-GPU-v100':
                bd_v100_running_container.append(task)
            elif task['label'] == '北京-GPU-V100':
                bj_v100_running_container.append(task)
            else:
                print(task)
        print("gz_cpu 运行任务数:%s" % len(gz_cpu_running_container))
        print("bd_cpu 运行任务数:%s" % len(bd_cpu_running_container))
        print("bd_v100 运行任务数:%s" % len(bd_v100_running_container))
        print("bj_v100 运行任务数:%s" % len(bj_v100_running_container))

        gz_cpu_running_container_list = self.addStillneedTime(
            gz_cpu_running_container, 'paddle-build')
        bd_cpu_running_container_list = self.addStillneedTime(
            bd_cpu_running_container, 'paddle-build')
        bd_v100_running_container_list = self.addStillneedTime(
            bd_v100_running_container, 'paddle-test')
        bj_v100_running_container_list = self.addStillneedTime(
            bj_v100_running_container, 'paddle-test')

        #V100/P4 旧集群
        xly_container_running_task_list = self.getJobList('running')
        old_p4_running_container = []
        old_v100_running_container = []
        for task in xly_container_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] == 'nTeslaP4':
                old_p4_running_container.append(task)
            elif task['label'] == 'nTeslaV100-16':
                old_v100_running_container.append(task)
        print("P4 运行任务数:%s" % len(old_p4_running_container))
        print("V100 运行任务数:%s" % len(old_v100_running_container))
        old_p4_running_container_list = self.addStillneedTime(
            old_p4_running_container)
        old_v100_running_container_list = self.addStillneedTime(
            old_v100_running_container)

        #SA机器
        xly_sa_running_task_list = self.getJobList('sarunning')
        sa_running_task_list = []
        for task in xly_sa_running_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] in self.Paddle_sa_cardType:
                sa_running_task_list.append(task)
        print("sa 运行任务数:%s" % len(sa_running_task_list))
        sa_running_task_list = self.addStillneedTime(sa_running_task_list)
        all_container_running_task_list = gz_cpu_running_container_list + bd_cpu_running_container_list + bd_v100_running_container_list + old_v100_running_container_list + old_p4_running_container_list + sa_running_task_list
        all_container_running_task_list = self.sortTime(
            all_container_running_task_list, 'stillneedTime', reverse=False)
        for task in all_container_running_task_list:
            target_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' % (
                task['bid'], task['jobId'])
            task[
                'target_url'] = '<a href=\"%s\" style=\"color: #337ab7; text-decoration: underline\">%s</a> ' % (
                    target_url, task['jobId'])
            task['target_url_ishtml'] = True

        with open("../buildLog/running_task.json", "w") as f:
            json.dump(all_container_running_task_list, f)
            f.close()

        return all_container_running_task_list

    def addStillneedTime(self, task_list, stage='paddle-time'):
        running_job_list = []
        execTime_dict = self.getExecTime()
        for task in task_list:
            ciName = task['name']
            if '-22' in ciName:
                ciName = ciName.replace('-22', '')
            if ciName.startswith(self.Paddle_container_ci
                                 ) and ciName != 'PR-CI-Coverage-Testtt':
                if stage == 'paddle-build':
                    diff_time = int(execTime_dict[ciName]['paddle-build'] -
                                    task['running'])
                else:
                    diff_time = int(execTime_dict[ciName]['paddle-test'] -
                                    task['running'])
                if diff_time == 0:
                    diff_time = 2
                elif diff_time < 0:
                    diff_time = 10  #如果过去2h成功的任务的平均时间-当前运行时间小于0，统一认为还有10min
                task['stillneedTime'] = diff_time
                running_job_list.append(task)
            elif ciName.startswith(self.Paddle_sa_ci) or ciName.startswith(
                    self.other_container_ci):
                if ciName in execTime_dict:
                    diff_time = int(execTime_dict[ciName]['paddle-time'] -
                                    task['running'])
                    if diff_time == 0:
                        diff_time = 2
                    elif diff_time < 0:
                        diff_time = 10  #如果过去2h成功的任务的平均时间-当前运行时间小于0，统一认为还有10min
                    task['stillneedTime'] = diff_time
                    running_job_list.append(task)
                else:
                    print("tttttttt: %s" % task)
            else:
                print("tttttttt: %s" % task)
                #task['stillneedTime'] = '-'
                #running_job_list.append(task)
        return running_job_list

    def classifyTaskByCardType(self, task_list, cardType_list):
        """
        this function will classify container tasks. eg nTeslaV100, nTeslaP4
        Args:
            container_task_list(list): 
            cardType(str): gpu card type. 
        Returns:
            cardType_task_list: .
        """
        print("cardType: %s" % cardType_list)
        task_list_by_card = []
        for task in task_list:
            if task['label'] in cardType_list:
                task_list_by_card.append(task)
        print(len(task_list_by_card))
        return task_list_by_card

    def addWaitingTaskTimeToStart(self, waiting_task, running_task,
                                  resourceType):
        """
        This function is to calculate how long the waiting task can start execution.
        Args:
            waiting_task(list): waiting task list.
            running_task(list): running task list.
            ci_list(list): ci list
        Returns:
            waiting_task(list): new waiting task list with TimeToStart.
        """
        execTime_dict = self.getExecTime()
        lastTaskToStartTime = 0
        for j in range(len(waiting_task)):
            ciName = waiting_task[j]['name']
            waiting_task[j]['commit'] = waiting_task[j]['commit'][0:6]
            waiting_task[j]['pid'] = str(waiting_task[j]['pid'])
            next_running_job = {}
            for key in waiting_task[j]:
                next_running_job[key] = waiting_task[j][key]
            if resourceType == 'CPU':
                if ciName in execTime_dict:
                    next_running_job['stillneedTime'] = execTime_dict[ciName][
                        'paddle-build']
                else:
                    print("%s not in DB----build !!" % ciName)
                    next_running_job['stillneedTime'] = 30
            elif resourceType == 'GPU':
                if ciName in execTime_dict:
                    if 'paddle-test' in execTime_dict[ciName]:
                        next_running_job['stillneedTime'] = execTime_dict[
                            ciName]['paddle-test']
                    else:
                        next_running_job['stillneedTime'] = execTime_dict[
                            ciName]['paddle-time']
                else:
                    print("%s not in DB-----test !!" % ciName)
                    next_running_job['stillneedTime'] = 60
            if len(running_task) == 0:
                waiting_task[j]['timeToStart'] = 10 + lastTaskToStartTime
                lastTaskToStartTime = lastTaskToStartTime + 10
            else:
                waiting_task[j]['timeToStart'] = int(running_task[0][
                    'stillneedTime'] + lastTaskToStartTime)
                lastTaskToStartTime = lastTaskToStartTime + running_task[0][
                    'stillneedTime']
                for i in range(1, len(running_task)):
                    new_stillneedTime = running_task[i][
                        'stillneedTime'] - running_task[0]['stillneedTime']
                    running_task[i]['stillneedTime'] = new_stillneedTime
                del (running_task[0])
            running_task.append(next_running_job)
            running_task = self.sortTime(
                running_task, 'stillneedTime', reverse=False)
        return waiting_task

    def sa_task_classification(self, sa_waiting_task_list,
                               sa_running_task_list):
        """
        将SA任务进行分类,获得新的排队列别
        """
        sa_cardType_task_dict = {}
        for task in sa_running_task_list:
            if task['label'] not in sa_cardType_task_dict:
                sa_cardType_task_dict[task['label']] = {
                    'running': [],
                    'waiting': []
                }
            sa_cardType_task_dict[task['label']]['running'].append(task)
        for task in sa_waiting_task_list:
            if task['label'] not in sa_cardType_task_dict:
                sa_cardType_task_dict[task['label']] = {
                    'running': [],
                    'waiting': []
                }
            sa_cardType_task_dict[task['label']]['waiting'].append(task)

        new_sa_waiting_task_list = []
        for key in sa_cardType_task_dict:
            sa_waiting_task_list = self.addWaitingTaskTimeToStart(
                sa_cardType_task_dict[key]['waiting'],
                sa_cardType_task_dict[key]['running'], 'GPU')
            for task in sa_waiting_task_list:
                new_sa_waiting_task_list.append(task)

        return new_sa_waiting_task_list

    def getWaitingJob(self):
        """
        this function will get all running list. Include containerJob and SaJob.
        Returns:
            all_running_task_list: all running job list.
        """
        ##cpu/gpu分离后的等待任务
        xly_container_cpu_gpu_waiting_task_list = self.getJobList(
            'cpu_gpu_waiting')
        gz_cpu_waiting_container = []
        bd_cpu_waiting_container = []
        bd_v100_waiting_container = []
        bj_v100_waiting_container = []
        for task in xly_container_cpu_gpu_waiting_task_list:
            if task['label'] == '广州-CPU集群':
                gz_cpu_waiting_container.append(task)
            elif task['label'] == '保定-CPU集群':
                bd_cpu_waiting_container.append(task)
            elif task['label'] == '保定-GPU-v100':
                bd_v100_waiting_container.append(task)
            elif task['label'] == '北京-GPU-V100':
                bj_v100_waiting_container.append(task)
            else:
                print(task)

        print("gz_cpu 等待任务数:%s" % len(gz_cpu_waiting_container))
        print("bd_cpu 等待任务数:%s" % len(bd_cpu_waiting_container))
        print("bd_v100 等待任务数:%s" % len(bd_v100_waiting_container))
        print("bj_v100 等待任务数:%s" % len(bj_v100_waiting_container))

        gz_cpu_container_waiting_task_list = self.sortTime(
            gz_cpu_waiting_container, 'waiting')
        gz_cpu_container_waiting_task_list = self.forwardReleaseBranchTask(
            gz_cpu_container_waiting_task_list)  #提前release分支
        bd_cpu_container_waiting_task_list = self.sortTime(
            bd_cpu_waiting_container, 'waiting')
        bd_cpu_container_waiting_task_list = self.forwardReleaseBranchTask(
            bd_cpu_container_waiting_task_list)  #提前release分支
        bd_v100_container_waiting_task_list = self.sortTime(
            bd_v100_waiting_container, 'waiting')
        bd_v100_container_waiting_task_list = self.forwardReleaseBranchTask(
            bd_v100_container_waiting_task_list)  #提前release分支
        bj_v100_container_waiting_task_list = self.sortTime(
            bj_v100_waiting_container, 'waiting')
        bj_v100_container_waiting_task_list = self.forwardReleaseBranchTask(
            bj_v100_container_waiting_task_list)  #提前release分支

        ##旧V100/P4等待任务
        xly_container_waiting_task_list = self.getJobList('waiting')
        old_p4_waiting_container = []
        old_v100_waiting_container = []
        for task in xly_container_waiting_task_list:
            if task['label'] == 'nTeslaP4':
                old_p4_waiting_container.append(task)
            elif task['label'] == 'nTeslaV100-16':
                old_v100_waiting_container.append(task)
            else:
                print(task)
        print("old p4 等待任务数:%s" % len(old_p4_waiting_container))
        print("old v100 等待任务数:%s" % len(old_v100_waiting_container))

        old_p4_container_waiting_task_list = self.sortTime(
            old_p4_waiting_container, 'waiting')
        old_p4_container_waiting_task_list = self.forwardReleaseBranchTask(
            old_p4_container_waiting_task_list)  #提前release分支
        old_v100_container_waiting_task_list = self.sortTime(
            old_v100_waiting_container, 'waiting')
        old_v100_container_waiting_task_list = self.forwardReleaseBranchTask(
            old_v100_container_waiting_task_list)  #提前release分支

        ##SA 等待任务
        xly_container_waiting_task_list = self.getJobList('sawaiting')
        sa_waiting_task = []
        for task in xly_container_waiting_task_list:
            task['pid'] = str(task['pid'])
            task['commit'] = task['commit'][0:6]
            if task['label'] in self.Paddle_sa_cardType:
                sa_waiting_task.append(task)
            else:
                if task['repoName'] not in [
                        'PaddlePaddle/Paddle-Lite'
                ] and task['label'] not in ['Paddle-git-clone', None]:
                    print("other sa task:%s" % task)

        print("sa 等待任务数:%s" % len(sa_waiting_task))

        sa_waiting_task_list = self.sortTime(sa_waiting_task, 'waiting')
        sa_waiting_task_list = self.forwardReleaseBranchTask(
            sa_waiting_task_list)  #提前release分支

        all_running_task_list = self.getRunningJob()
        gz_cpu_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['广州-CPU集群'])
        bd_cpu_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['保定-CPU集群'])
        bd_v100_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['保定-GPU-v100'])
        bj_v100_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['北京-GPU-V100'])

        print("bj_v100_running_task_list: %s" % bj_v100_running_task_list)

        old_p4_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['nTeslaP4'])
        old_v100_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, ['nTeslaV100-16'])

        sa_running_task_list = self.classifyTaskByCardType(
            all_running_task_list, self.Paddle_sa_cardType)

        new_gz_cpu_container_waiting_task_list = self.addWaitingTaskTimeToStart(
            gz_cpu_container_waiting_task_list, gz_cpu_running_task_list,
            'CPU')
        new_bd_cpu_container_waiting_task_list = self.addWaitingTaskTimeToStart(
            bd_cpu_container_waiting_task_list, bd_cpu_running_task_list,
            'CPU')
        new_bd_v100_container_waiting_task_list = self.addWaitingTaskTimeToStart(
            bd_v100_container_waiting_task_list, bd_v100_running_task_list,
            'GPU')
        new_bj_v100_container_waiting_task_list = self.addWaitingTaskTimeToStart(
            bj_v100_container_waiting_task_list, bj_v100_running_task_list,
            'GPU')

        new_old_p4_container_waiting_task_list = self.addWaitingTaskTimeToStart(
            old_p4_container_waiting_task_list, old_p4_running_task_list,
            'GPU')
        #new_old_v100_container_waiting_task_list = self.addWaitingTaskTimeToStart(old_v100_container_waiting_task_list, old_v100_running_task_list, 'GPU')

        new_sa_waiting_task_list = self.sa_task_classification(
            sa_waiting_task_list, sa_running_task_list)

        all_waiting_task_list = new_gz_cpu_container_waiting_task_list + new_bd_cpu_container_waiting_task_list + new_bd_v100_container_waiting_task_list + new_old_p4_container_waiting_task_list + new_bj_v100_container_waiting_task_list + new_sa_waiting_task_list
        new_all_waiting_task = self.sortTime(
            all_waiting_task_list, 'timeToStart', reverse=False)
        with open("../buildLog/wait_task.json", "w") as f:
            json.dump(new_all_waiting_task, f)
            f.close()


getQueueUpCIList().getWaitingJob()
