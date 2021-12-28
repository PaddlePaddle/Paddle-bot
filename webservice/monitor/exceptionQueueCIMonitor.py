import json
import time
import sys
sys.path.append("..")
from utils.resource import Resource
from utils.mail import Mail


class ExceptionWaitingJob(Resource):
    """异常排队作业"""

    def __init__(self):
        self.required_labels = [
            '保定-GPU-v100', '北京-GPU-V100', '广州-CPU集群', '保定-CPU集群',
            'Paddle-mac-py3', 'Paddle-windows', 'Paddle-windows-cpu',
            'Paddle-Kunlun', 'Paddle-musl', 'Paddle-approval-cpu'
        ]
        self.__resource = self.getEachResource()
        self.__longest_waiting_default = 30

    def getEachResourceDict(self):
        ResourceDict = {}
        for label in self.required_labels:
            if label not in [
                    '保定-GPU-v100', '北京-GPU-V100', '广州-CPU集群', '保定-CPU集群',
                    'nTeslaV100-16', 'nTeslaP4'
            ]:
                ResourceDict[label] = self.__resource[label]
        ResourceDict['nTeslaV100-16'] = 3
        ResourceDict['nTeslaP4'] = 9
        ResourceDict['保定-GPU-v100'] = 15
        ResourceDict['北京-GPU-V100'] = 10
        ResourceDict['广州-CPU集群'] = 16
        ResourceDict['保定-CPU集群'] = 24
        return ResourceDict

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
        return len(task_list_by_card)

    def getRunningJobSize(self):
        """
        this function will get size of running job list in different types.
        """
        with open("../buildLog/running_task.json", 'r') as load_f:
            all_running_task = json.load(load_f)
            load_f.close()
        running_job_size = {}
        for label in self.required_labels:
            running_job_size[label] = self.classifyTaskByCardType(
                all_running_task, label)
        print(running_job_size)
        return running_job_size

    def getExceptionWaitingJob(self):
        """
        this function will get Exception WaitingJob.
        """
        running_job_size = self.getRunningJobSize()
        ResourceDict = self.getEachResourceDict()
        with open("../buildLog/wait_task.json", 'r') as load_f:
            all_waiting_task = json.load(load_f)
            load_f.close()
        mailContent = ''
        for task in all_waiting_task:
            if task['waiting'] > self.__longest_waiting_default:
                for label in self.required_labels:
                    if task['label'] == label:
                        print("label: %s" % label)
                        real_use_count = running_job_size[label]
                        print(real_use_count)
                        resource_count = ResourceDict[label]
                        print("resource_count: %s" % resource_count)
                        isAbnormal = self.getIsAbnormal(resource_count,
                                                        real_use_count)
                        if isAbnormal == True:
                            mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                                task['PR'], task['CIName'], task['waiting'],
                                task['cardType'], real_use_count,
                                resource_count, task['repoName'])

        return mailContent

    def exactExceptionAlarm(self):
        count = 1

        mailContent = self.getExceptionWaitingJob()
        print(mailContent)
        mailBeginning = "<html><body><p>Hi, ALL:</p> <p>以下任务已等待超过60min, 且对应的资源并不是全在使用, 请及时查看.</p><table border='1' align=center> <caption><font size='3'><b>等待超过60min的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已等待时间/min</td><td bgcolor='#d0d0d0'>使用资源</td><td bgcolor='#d0d0d0'>实际使用资源个数/个</td><td bgcolor='#d0d0d0'>资源全量/个</td><td bgcolor='#d0d0d0'>repo</td></tr>"
        while count < 4 and mailContent != '':
            print("count: %s" % count)
            print("mailContent: %s" % mailContent)
            time.sleep(60)
            mailContent = self.getExceptionWaitingJob()
            count += 1  #最多请求3次
        if mailContent != '':
            mailDetails = mailBeginning + mailContent + '</body></html>'
            self.sendMail(mailDetails)
        else:
            print("资源正常!")

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
        mail.set_sender('xx@baidu.com')
        mail.set_receivers(['xx@baidu.com'])
        mail.set_title('[告警]任务等待超时, 资源异常')
        mail.set_message(mailContent, messageType='html', encoding='gb2312')
        mail.send()


ExceptionWaitingJob().exactExceptionAlarm()
