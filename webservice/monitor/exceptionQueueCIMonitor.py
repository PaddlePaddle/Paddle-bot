import json
import sys
sys.path.append("..")
from utils.mail import Mail


class ExceptionWaitingJob():
    """异常排队作业"""

    def __init__(self):
        self.__longest_waiting_default = 60
        self.__v100_count = 17
        self.__p4_count = 5
        self.__mac_count = 4
        self.__macpy3_count = 3
        self.__win_count = 14
        self.__winopenblas_count = 9
        self.__approval_count = 1
        self.__benchmark_count = 1
        self.__cinn_count = 1

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
        return len(task_list_by_card)

    def getRunningJobSize(self):
        """
        this function will get size of running job list in different types.
        """
        running_job_size = {}
        with open("../buildLog/running_task.json", 'r') as load_f:
            all_running_task = json.load(load_f)
            load_f.close()
        running_job_size['v100'] = self.classifyTaskByCardType(
            all_running_task, 'v100')
        running_job_size['p4'] = self.classifyTaskByCardType(all_running_task,
                                                             'p4')
        running_job_size['win'] = self.classifyTaskByCardType(all_running_task,
                                                              'win')
        running_job_size['winopenblas'] = self.classifyTaskByCardType(
            all_running_task, 'winopenblas')
        running_job_size['mac'] = self.classifyTaskByCardType(all_running_task,
                                                              'mac')
        running_job_size['macpy3'] = self.classifyTaskByCardType(
            all_running_task, 'macpy3')
        running_job_size['approval'] = self.classifyTaskByCardType(
            all_running_task, 'approval')
        running_job_size['benchmark'] = self.classifyTaskByCardType(
            all_running_task, 'benchmark')
        running_job_size['cinn'] = self.classifyTaskByCardType(
            all_running_task, 'cinn')
        print(running_job_size)
        return running_job_size

    def getExceptionWaitingJob(self):
        """
        this function will get Exception WaitingJob.
        """
        running_job_size = self.getRunningJobSize()
        with open("../buildLog/wait_task.json", 'r') as load_f:
            all_waiting_task = json.load(load_f)
            load_f.close()
        mailBeginning = "<html><body><p>Hi, ALL:</p> <p>以下任务已等待超过60min, 且对应的资源并不是全在使用, 请及时查看.</p><table border='1' align=center> <caption><font size='3'><b>等待超过60min的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已等待时间/min</td><td bgcolor='#d0d0d0'>使用资源</td><td bgcolor='#d0d0d0'>实际使用资源个数/个</td><td bgcolor='#d0d0d0'>资源全量/个</td><td bgcolor='#d0d0d0'>repo</td></tr>"
        mailContent = ''
        for task in all_waiting_task:
            if task['waiting'] > self.__longest_waiting_default:
                if 'v100' in task['cardType'].lower():
                    real_use_count = running_job_size['v100']
                    resource_count = self.__v100_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'p4' in task['cardType'].lower():
                    real_use_count = running_job_size['p4']
                    resource_count = self.__p4_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'mac' in task['cardType'].lower() and not task[
                        'CIName'].startswith('PR-CI-Mac-Python3'):
                    real_use_count = running_job_size['mac']
                    resource_count = self.__mac_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'macpy3' in task['cardType'].lower():
                    real_use_count = running_job_size['macpy3']
                    resource_count = self.__macpy3_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'win' in task['cardType'].lower() and not task[
                        'CIName'].startswith('PR-CI-Windows-OPENBLAS'):
                    real_use_count = running_job_size['win']
                    resource_count = self.__win_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'winopenblas' in task['cardType'].lower():
                    real_use_count = running_job_size['winopenblas']
                    resource_count = self.__winopenblas_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'approval' in task['cardType'].lower():
                    real_use_count = running_job_size['approval']
                    resource_count = self.__approval_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'benchmark' in task['cardType'].lower():
                    real_use_count = running_job_size['benchmark']
                    resource_count = self.__benchmark_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                elif 'cinn' in task['cardType'].lower():
                    real_use_count = running_job_size['cinn']
                    resource_count = self.__cinn_count
                    isAbnormal = self.getIsAbnormal(resource_count,
                                                    real_use_count)
                else:
                    print('OTHER TYPE %s: %s' % (task['cardType'], task))
                    isAbnormal = False
                if isAbnormal == True:
                    mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                        task['PR'], task['CIName'], task['waiting'],
                        task['cardType'], real_use_count, resource_count,
                        task['repoName'])
        if mailContent != '':
            mailDetails = mailBeginning + mailContent + '</body></html>'
            self.sendMail(mailDetails)

    def getIsAbnormal(self, default_count, running_count):
        """
        this function will get the WaitingJob is ifAbnormal.
        Returns:
            isAbnormal(bool): True/False
        """
        isAbnormal = False
        ratio = (default_count - running_count) / default_count
        if ratio > 0.25:
            isAbnormal = True
        return isAbnormal

    def sendMail(self, mailContent):
        """
        this function will send alarm mail.
        """
        mail = Mail()
        mail.set_sender('xxx@baidu.com')
        mail.set_receivers(['xx@baidu.com'])
        mail.set_title('[告警]任务等待超时')
        mail.set_message(mailContent, messageType='html', encoding='gb2312')
        mail.send()


ExceptionWaitingJob().getExceptionWaitingJob()
