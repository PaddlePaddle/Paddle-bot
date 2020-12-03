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
        self.container_cardType = ['v100', 'p4']
        self.sa_cardType = [
            'win', 'mac', 'cpu', 'benchmark', 'cinn', 'approval'
        ]  # 'kunlun', 'cinn

        self.container_ci = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-CPU-Py2', 'PR-CI-Inference',
            'xly-PR-CI-PY35', 'xly-PR-CI-PY27', 'FluidDoc1', 'build-paddle',
            'xly-PR-CI-PY2', 'xly-PR-CI-PY3', 'PR-CI-CUDA9-CUDNN7',
            'PaddleServing文档测试'
        ]
        self.sa_ci = [
            'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS', 'PR-CI-Mac',
            'PR-CI-Mac-Python3', 'PR-CI-APPROVAL', 'PR-CI-OP-Benchmark',
            'cinn-ci'
        ]

        self.v100_ci = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'xly-PR-CI-PY35', 'xly-PR-CI-PY27',
            'xly-PR-CI-PY2', 'xly-PR-CI-PY3', 'PR-CI-CUDA9-CUDNN7',
            'PaddleServing文档测试'
        ]
        self.p4_ci = [
            'PR-CI-CPU-Py2', 'PR-CI-Inference', 'FluidDoc1', 'build-paddle'
        ]
        self.win_ci = ['PR-CI-Windows']
        self.winopenblas_ci = ['PR-CI-Windows-OPENBLAS']
        self.mac_ci = ['PR-CI-Mac']
        self.macpy3_ci = ['PR-CI-Mac-Python3']
        self.approval_ci = ['PR-CI-APPROVAL']
        self.benchmark_ci = ['PR-CI-OP-Benchmark']
        self.cinn_ci = ['cinn-ci']

    def sortTime(self, task_list, key, reverse=True):
        if len(task_list) != 0:
            task_list = sorted(
                task_list, key=lambda e: e.__getitem__(key), reverse=reverse)
        return task_list

    def forwardReleaseBranchTask(self, task_list):
        task_relese = []
        for task in task_list:
            if '-18' in task['CIName'] or '-20' in task['CIName']:
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

    def addStillneedTime(self, task_list, ci_list):
        """
        this function will add stillneedTime in running job.
        Args:
            task_list(list): running job list.
            ci_list(list): ci list distinguished by card.
        Returns:
            result: 
        """
        execTime_dict = self.getExecTime()

        running_task_list = []
        for task in task_list:
            for ci in ci_list:
                if task['CIName'].startswith(
                        'PR-CI-Windows-OPENBLAS') and ci == 'PR-CI-Windows':
                    continue
                if task['CIName'].startswith(
                        'PR-CI-Mac-Python3') and ci == 'PR-CI-Mac':
                    continue
                key = '%s_%s_%s' % (ci, task['repoName'], task['ifDocument'])
                if task['CIName'].startswith(ci):
                    stillneedTime = execTime_dict[key] - task['running']
                    if stillneedTime <= 0:
                        stillneedTime = 10  #如果已经超过平均时间，统一认为还需要10min
                    task['stillneedTime'] = stillneedTime
                    running_task_list.append(task)
                    break
        return running_task_list

    def getRunningJob(self):
        """
        this function will get all running list. Include containerJob and SaJob.
        Returns:
            all_running_task_list: all running job list.
        """
        xly_container_running_task_list = self.getJobList('running')
        container_running_task_list = self.xlyJobToRequired(
            xly_container_running_task_list, 'running',
            self.container_cardType)
        container_running_task_list = self.addStillneedTime(
            container_running_task_list, self.container_ci)

        xly_sa_running_task_list = self.getJobList('sarunning')
        sa_running_task_list = self.xlyJobToRequired(
            xly_sa_running_task_list, 'sarunning', self.sa_cardType)
        sa_running_task_list = self.addStillneedTime(sa_running_task_list,
                                                     self.sa_ci)

        all_running_task_list = container_running_task_list + sa_running_task_list
        all_running_task_list = self.sortTime(
            all_running_task_list, 'stillneedTime', reverse=False)
        with open("../buildLog/running_task.json", "w") as f:
            json.dump(all_running_task_list, f)
            f.close()
        return all_running_task_list

    def classifyTaskByCardType(self, task_list, cardType):
        """
        this function will classify container tasks. eg nTeslaV100, nTeslaP4
        Args:
            container_task_list(list): 
            cardType(str): gpu card type. 
        Returns:
            cardType_task_list: .
        """
        task_list_by_card = []
        for task in task_list:
            if cardType == 'mac' and task['CIName'].startswith(
                    'PR-CI-Mac-Python3'):
                continue
            if cardType == 'win' and task['CIName'].startswith(
                    'PR-CI-Windows-OPENBLAS'):
                continue
            if cardType.lower() in task['cardType'].lower():
                task_list_by_card.append(task)
        return task_list_by_card

    def addWaitingTaskTimeToStart(self, waiting_task, running_task, ci_list):
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
            next_running_job = {}
            for key in waiting_task[j]:
                next_running_job[key] = waiting_task[j][key]
            for ci in ci_list:
                key = '%s_%s_%s' % (ci, next_running_job['repoName'],
                                    next_running_job['ifDocument'])
                if next_running_job['CIName'].lower().startswith(ci.lower()):
                    next_running_job['stillneedTime'] = execTime_dict[key]
                elif 'TEST-Windows' in next_running_job['CIName']:
                    next_running_job['stillneedTime'] = execTime_dict[
                        'PR-CI-Windows_PaddlePaddle/Paddle_False']
                elif 'PR-CI-Pretest-Ignore' in next_running_job['CIName']:
                    next_running_job['stillneedTime'] = execTime_dict[
                        'PR-CI-Coverage_PaddlePaddle/Paddle_False']
                elif 'PaddleServing文档测试' in next_running_job['CIName']:
                    next_running_job['stillneedTime'] = execTime_dict[
                        'PaddleServing文档测试_PaddlePaddle/Serving_False']
                elif 'PR-CI-OP-benchmark-TEST' in next_running_job['CIName']:
                    next_running_job['stillneedTime'] = 60
            if len(running_task) == 0:
                waiting_task[j]['timeToStart'] = 1 + lastTaskToStartTime
                lastTaskToStartTime = lastTaskToStartTime + 1
            else:
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
            running_task = self.sortTime(
                running_task, 'stillneedTime', reverse=False)

        return waiting_task

    def xlyJobToRequired(self, jobList, jobStatus, cardType_list):
        """
        This function is to convert xly's task list to the required task list.
        Args:
            jobList(list): xly's  task list.
            jobStatus(str): job status (running/sarunning/waiting/sawaiting).
            cardType_list(list): card type list.
        Returns:
            all_task_list(list): the required task list.
        """
        all_task_list = []
        for t in jobList:
            if t['label'] not in ['Paddle-musl']:  #musl这条现在不需要管
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
                if t['repoName'] in [
                        'PaddlePaddle/Paddle'
                ]:  #Paddle repo need to check if Document_fix 
                    task['ifDocument'] = self.ifDocumentByCommitId(
                        t['commit'], t['repoName'])
                else:
                    task['ifDocument'] = False
                for cardType in cardType_list:
                    if cardType.lower() in task['cardType'].lower() and t[
                            'jobName'] not in ['构建镜像', 'build-docker-image']:
                        if task['repoName'] in [
                                'PaddlePaddle/Paddle',
                                'PaddlePaddle/benchmark',
                                'PaddlePaddle/FluidDoc',
                                'PaddlePaddle/PaddleRec', 'PaddlePaddle/CINN',
                                'PaddlePaddle/Serving'
                        ]:
                            all_task_list.append(task)
                        else:
                            print('OTHER REPO: %s' % task)
                        break
        return all_task_list

    def getWaitingJob(self):
        """
        this function will get all running list. Include containerJob and SaJob.
        Returns:
            all_running_task_list: all running job list.
        """
        xly_container_waiting_task_list = self.getJobList('waiting')
        container_waiting_task_list = self.xlyJobToRequired(
            xly_container_waiting_task_list, 'waiting',
            self.container_cardType)
        xly_sa_waiting_task_list = self.getJobList('sawaiting')
        sa_waiting_task_list = self.xlyJobToRequired(
            xly_sa_waiting_task_list, 'sawaiting', self.sa_cardType)
        if len(container_waiting_task_list) == 0 and len(
                sa_waiting_task_list) == 0:
            with open("../buildLog/wait_task.json", "w") as f:
                json.dump([], f)
                f.close()
            all_running_task_list = self.getRunningJob()
        else:
            #容器中等待的作业分为两类: v100/p4            
            container_waiting_task_list = self.sortTime(
                container_waiting_task_list, 'waiting')
            container_waiting_task_list = self.forwardReleaseBranchTask(
                container_waiting_task_list)  #提前release分支
            v100_waiting_task_list = self.classifyTaskByCardType(
                container_waiting_task_list, 'v100')
            p4_waiting_task_list = self.classifyTaskByCardType(
                container_waiting_task_list, 'p4')

            #sa中等待的作业分为: win/mac/approval/benchmark/cinn
            sa_waiting_task_list = self.sortTime(sa_waiting_task_list,
                                                 'waiting')
            sa_waiting_task_list = self.forwardReleaseBranchTask(
                sa_waiting_task_list)  #提前release分支
            win_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'win')
            winopenblas_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'winopenblas')
            mac_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'mac')
            macpy3_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'macpy3')
            approval_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'approval')
            benchmark_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'benchmark')
            cinn_waiting_task_list = self.classifyTaskByCardType(
                sa_waiting_task_list, 'cinn')

            all_running_task_list = self.getRunningJob()

            #容器中运行的作业分为两类: v100/p4
            v100_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'v100')

            p4_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'p4')
            #sa中运行的作业分为: win/mac/approval/benchmark/cinn
            win_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'win')
            winopenblas_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'winopenblas')
            mac_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'mac')
            macpy3_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'macpy3')
            approval_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'approval')
            benchmark_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'benchmark')
            cinn_running_task_list = self.classifyTaskByCardType(
                all_running_task_list, 'cinn')

            new_v100_waiting_task_list = self.addWaitingTaskTimeToStart(
                v100_waiting_task_list, v100_running_task_list, self.v100_ci)
            new_p4_waiting_task_list = self.addWaitingTaskTimeToStart(
                p4_waiting_task_list, p4_running_task_list, self.p4_ci)
            new_win_waiting_task_list = self.addWaitingTaskTimeToStart(
                win_waiting_task_list, win_running_task_list, self.win_ci)
            new_winopenblas_waiting_task_list = self.addWaitingTaskTimeToStart(
                winopenblas_waiting_task_list, winopenblas_running_task_list,
                self.winopenblas_ci)
            new_mac_waiting_task_list = self.addWaitingTaskTimeToStart(
                mac_waiting_task_list, mac_running_task_list, self.mac_ci)
            new_macpy3_waiting_task_list = self.addWaitingTaskTimeToStart(
                macpy3_waiting_task_list, macpy3_running_task_list,
                self.macpy3_ci)
            new_approval_waiting_task_list = self.addWaitingTaskTimeToStart(
                approval_waiting_task_list, approval_running_task_list,
                self.approval_ci)
            new_benchmark_waiting_task_list = self.addWaitingTaskTimeToStart(
                benchmark_waiting_task_list, benchmark_running_task_list,
                self.benchmark_ci)
            new_cinn_waiting_task_list = self.addWaitingTaskTimeToStart(
                cinn_waiting_task_list, cinn_running_task_list, self.cinn_ci)

            new_all_waiting_task = new_v100_waiting_task_list + new_p4_waiting_task_list + new_win_waiting_task_list + new_winopenblas_waiting_task_list + new_mac_waiting_task_list + new_macpy3_waiting_task_list + new_approval_waiting_task_list + new_benchmark_waiting_task_list + new_cinn_waiting_task_list
            new_all_waiting_task = self.sortTime(
                new_all_waiting_task, 'timeToStart', reverse=False)
            with open("../buildLog/wait_task.json", "w") as f:
                json.dump(new_all_waiting_task, f)
                f.close()


getQueueUpCIList().getWaitingJob()
