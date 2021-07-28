import requests
import json
import sys
sys.path.append("..")
from utils.test_auth_ipipe import xlyOpenApiRequest
from utils.mail import Mail
from utils.handler import xlyHandler, PRHandler
from utils.common import CommonModule
import os
import time
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, filename='../logs/killTimeoutJob.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class killTimeoutRunningJob(xlyHandler, PRHandler, CommonModule):
    """取消超时任务"""
    def __init__(self):
        self.__container_cardType = ['nTeslaV100', 'nTeslaP4']
        self.__sa_cardType = ['win', 'mac', 'benchmark', 'cinn', 'approval']# 'kunlun' 
        self.__coverage_timeout_default = 180
        self.__py3_timeout_default = 120
        self.__win_timeout_default = 240
        self.__winopenblas_timeout_default = 80
        self.__p4_timeout_default = 60
        self.__mac_timeout_default = 60
        self.__approval_timeout_default = 15
        self.__build_paddle_timeout_default = 40

    def create_failed_cause_csv(self, kill_file):
        """创建存储文件"""
        df = pd.DataFrame(columns=['TIME','PR', 'COMMITID', 'CINAME', 'RUNNINGTIME', 'TASKURL'])
        df.to_csv(kill_file)

    def save_cancel_job(self, data):
        """将kill的任务存到"""
        kill_file = '../buildLog/kill_timeout_runninng_job.csv'
        if os.path.exists(kill_file) == False :
            create_failed_cause_csv(kill_file)
        write_data = pd.DataFrame(data)
        write_data.to_csv(kill_file, mode='a', header=False)

    def filter_timeout_task(self):
        """
        返回：真正超时且要取消的任务列表, 仅告警但不取消的任务列表
        """
        with open("../buildLog/running_task.json", 'r') as load_f:
            all_running_task = json.load(load_f)
            load_f.close()
        print(all_running_task)

        timeout_running_job = []
        alarm_running_job = []
        for task in all_running_task:
            print(task)
            ifdockerfile = self.ifDockerFile(task['repoName'], task['commitId'])
            print('ifdockerfile: %s' %ifdockerfile)
            if ifdockerfile == False:
                if 'nTeslaP4' in task['cardType']:
                    if task['CIName'].startswith('build-paddle'):
                        if task['running'] > self.__build_paddle_timeout_default:
                            timeout_running_job.append(task)
                    elif task['running'] > self.__p4_timeout_default:
                        timeout_running_job.append(task)
                elif 'nTeslaV100' in task['cardType']:
                    if task['CIName'].startswith('PR-CI-Py3'):
                        if task['running'] > self.__py3_timeout_default:
                            timeout_running_job.append(task)
                    elif task['CIName'].startswith('PR-CI-Coverage'): 
                        if task['running'] > self.__coverage_timeout_default:
                            timeout_running_job.append(task)
                    else:
                        if task['running'] > 60: #v100任务大于60min 要报警
                            alarm_running_job.append(task)
                            logger.info('%s has running %s' %(task['CIName'], task['running']))
                elif 'mac' in task['cardType']:
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
                        logger.info('%s has running %s' %(task['CIName'], task['running']))
            else:
                print("Dockerfile: %s" %task)
                logger.info("Dockerfile: %s" %task)
        print("timeout_running_job")
        print(timeout_running_job)
        print("===")
        print("alarm_running_job")
        print(alarm_running_job)
        return timeout_running_job, alarm_running_job

    def kill_rerun_job(self):
        """
        1. 先取消
        2. 取消后需要看是否可以rerun
        """
        timeout_running_job, alarm_running_job = self.filter_timeout_task()
        mailContent = ''
        if len(timeout_running_job) > 0:
            mailContent += " <p>以下任务被判定为运行超时, 已自动取消, rerun情况如下表, 请排查超时原因！</p> <p>超时规则: Coverage超过180min, Py3超过120min, Inference/CPU 超过60min, Mac/Mac-python3 超过60min, Windows超过240min, Windows-OPENBLAS超过80min</p> <table border='1' align=center> <caption><font size='3'><b>自动取消运行中的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>是否rerun</td><td bgcolor='#d0d0d0'>任务链接</td></tr>"
            for task in timeout_running_job:
                #先检测是否具备rerun的前提, 在进行取消, 否则对判断rerun有影响
                stage_message = self.getStageMessge(task['targetId'])
                create_time = int(str(stage_message['pipelineBuildBean']['startTime'])[:-3])
                agile_workspace = stage_message['pipelineBuildBean']['stageBuildBeans'][0]['outParams']['AGILE_WORKSPACE']
                target_url = 'https://xly.bce.baidu.com/paddlepaddle/%s/newipipe/detail/%s/job/%s' %(agile_workspace, task['targetId'], task['jobId'])
                triggerId = stage_message['triggerId']
                if task['CIName'].startswith('build-paddle'):
                    canRerun = True
                else:
                    canRerun = self.ifCanRerun(task['repoName'], task['commitId'], task['CIName'], create_time)
                data = {'TIME': time.strftime("%Y%m%d %H:%M:%S", time.localtime()), 'PR': task['PR'],  'COMMITID': task['commitId'], 'CINAME': task['CIName'], 'RUNNINGTIME': [task['running']], 'TASKURL': target_url}
                self.save_cancel_job(data)
                res = self.cancelJob(task['jobId'])
                print(res)
                print(res.status_code)
                if res.status_code == 200 or res.status_code == 201:
                    mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td>" %(task['PR'], task['CIName'], task['running'])  
                    if canRerun == True:
                        time.sleep(10)
                        rerun_task = self.rerunJob(triggerId)
                        print("rerun_task: %s" %rerun_task)
                        if rerun_task.status_code == 200 or rerun_task.status_code == 201:
                            mailContent += "<td>True</td><td>%s</td></tr>" %target_url
                        else:
                            mailContent += "<td>False</td><td>%s</td></tr>" %target_url
                else:
                    mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td>" %(task['PR'], task['CIName'], '取消作业失败！！')      
                    mailContent += "<td>False</td><td>%s</td></tr>" %target_url
            mailContent += "</table>"
            
        if len(alarm_running_job) > 0: 
            mailContent += "<p>此外, 以下任务已经运行超过60min, 请查看任务是否卡住.</p>"
            mailContent += "<table border='1' align=center> <caption><font size='3'><b>任务已运行超过60min</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>repo</td><td bgcolor='#d0d0d0'>任务链接</td></tr>"
            for task in alarm_running_job:
                stage_message = self.getStageMessge(task['targetId'])
                agile_workspace = stage_message['pipelineBuildBean']['stageBuildBeans'][0]['outParams']['AGILE_WORKSPACE']
                task_url = 'https://xly.bce.baidu.com/paddlepaddle/%s/newipipe/detail/%s/job/%s' %(agile_workspace, task['targetId'], task['jobId'])
                mailContent += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %(task['PR'], task['CIName'], task['running'], task['repoName'], task_url)  
            mailContent += "</table>"
        print("mailContent")
        print(mailContent)

        if mailContent != '':
            self.sendMail(mailContent)
    
    def ifCanRerun(self, repoName, commitId, CIName, createTime):
        """
        判断当前commit是否是最新的commit
        有的PR已经被rerun过了或者已经有了最终的状态, 此部分只要取消掉即可
        """
        canRerun = False
        status_url = 'https://api.github.com/repos/%s/statuses/%s' %(repoName, commitId) 
        print(status_url)
        res = requests.get(status_url, headers = {'Authorization': 'token a762b6a23d26027ac70ae96b34717baa13a5fa7e'})
        ci_list = []
        for ci in res.json():
            if ci['context'] == CIName:
                already_exit = False
                for i in ci_list:
                    if i['time'] > ci['created_at']:
                        already_exit = True
                        break
                if already_exit == False:
                    item_dic = {}
                    item_dic['CIName'] = ci['context']
                    item_dic['time'] = ci['created_at']
                    item_dic['status'] = ci['state']
                    ci_list.append(item_dic)
        print(ci_list)
        utc_time = ci_list[0]['time']
        ci_lastest_time = str(self.utcTimeToStrTime(utc_time))
        ci_lastest_time_stamp = self.strTimeToTimestamp(ci_lastest_time)
        if abs(ci_lastest_time_stamp - createTime) < 30 or ci_lastest_time_stamp: #commit最新的ci如果比当前ci差不多(两个时间差小于30s，认为这俩作业是一个作业，那么就该rerun)
            canRerun = True
        print("canRerun: %s" %canRerun)
        return canRerun
    
    def sendMail(self, mailContent):
        HTML_CONTENT = "<html><body><p>Hi, ALL:</p>"
        HTML_CONTENT += mailContent
        HTML_CONTENT += "<p>如有问题，请联系张春乐.</p> <p>张春乐</p></body></html>"
        mail = Mail()
        mail.set_sender('zhangchunle@baidu.com')
        mail.set_receivers(['zhangchunle@baidu.com', 'tianshuo03@baidu.com', 'v_duchun@baidu.com', 'luotao02@baidu.com', 'zhouwei25@baidu.com', 'wanghuan29@baidu.com', 'wuhuanzhou@baidu.com'])
        mail.set_title('[告警]自动取消超时任务')
        mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
        mail.send()

killTimeoutRunningJob().kill_rerun_job()