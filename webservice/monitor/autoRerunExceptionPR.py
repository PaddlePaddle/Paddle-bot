import json
import time
import datetime
import os
import requests
import sys
sys.path.append("..")
from utils.handler import xlyHandler
from utils.readConfig import ReadConfig
from utils.mail import Mail
from utils.common import CommonModule

localConfig = ReadConfig('../conf/config.ini')

class autoRerunExceptionPR(xlyHandler, CommonModule):
    """
    1. 获取正在运行的任务
    2. 判断任务是否卡住: 最后一行日志的时间距离当前时间大于30min 
    3. 卡住就rerun
    """
    def autoMarkandRerunJob(self):
        with open("../buildLog/running_task.json", 'r') as load_f:
            all_running_task = json.load(load_f)
            load_f.close()
        print(all_running_task)
        content = ''
        for task in all_running_task:
            if task['running'] > 20 and task['CIName'].startswith(('PR-CI-Windows', 'PR-CI-Coverage')):
                print(task)
                target_url = "https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s" %(task['targetId'], task['jobId'])
                stage_message = self.getStageMessge(task['targetId'])
                jobGroupBuildBeans = stage_message['pipelineBuildBean']['stageBuildBeans'][0]['jobGroupBuildBeans'][0]
                create_time = int(str(stage_message['pipelineBuildBean']['startTime'])[:-3])
                print(create_time)
                triggerId = stage_message['triggerId'] #rerun id
                print("triggerId: %s" %triggerId)
                for job in jobGroupBuildBeans:
                    jobName = job['jobName']
                    if jobName not in ['构建镜像', 'build-docker-image']:
                        if task['CIName'].startswith(('PR-CI-Windows')):
                            taskid = job['realJobBuild']['shellBuild']['taskId']
                            logUrl = "https://xly.bce.baidu.com/paddlepaddle/paddle-ci/sa_log/log/download/%s" %taskid
                        else:           
                            logParam = job['realJobBuild']['logUrl']
                            taskid = logParam.split('=')[1].split('&')[0]
                            logUrl = localConfig.cf.get('ipipeConf', 'log_url') + logParam
                        filename = '../buildLog/%s_%s_%s.log' %(task['PR'], task['CIName'], taskid)
                        self.getJobLog(filename, logUrl)
                        isstuck = self.ifStuck(filename)
                        if isstuck == True:
                            canRerun = self.ifCanRerun(task['repoName'], task['commitId'], task['CIName'], create_time)
                            content += "<tr align=center><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %(task['PR'], task['CIName'], task['commitId'], task['running'], canRerun, target_url)
                            
                            #if canRerun == True:
                            #    cancel_task = self.cancelJob(task['jobId'])
                            #    print("cancel_task: %s" %cancel_task)
                            #    time.sleep(10)
                            #    rerun_task = self.rerunJob(triggerId)
                            #    print("rerun_task: %s" %rerun_task)
                            #else:
                            #    cancel_task = self.cancelJob(task['jobId'])  
                                        
        return content

    def ifCanRerun(self, repoName, commitId, CIName, createTime):
        """
        有的PR已经被rerun过了或者已经有了最终的状态, 此部分只要取消掉即可
        """
        canRerun = False
        status_url = 'https://api.github.com/repos/%s/statuses/%s' %(repoName, commitId) 
        print(status_url)
        res = requests.get(status_url, headers = {'Authorization': 'token a762b6a23d26027ac70ae96b34717baa13a5fa7e'})
        print(res.text)
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

    def ifStuck(self, filename):
        isstuck = False
        print('filename: %s' %filename)
        with open('%s' %filename, 'r') as f:
            lines = f.readlines()
            last_line = lines[-1]
            if 'sleep 1000h' in last_line: #test ci
                print('It is a test ci.')
            else:
                last_line_time_list = last_line.split(' ', 2)
                lastest_time = '%s %s' %(last_line_time_list[0], last_line_time_list[1])
                print(lastest_time)
                lastest_time_stamp = self.strTimeToTimestamp(lastest_time)
                current_time_stamp = int(time.time())
                if current_time_stamp - lastest_time_stamp > 30 * 60: #当前时间-最新的时间 >30min
                    isstuck = True
        print("isstuck: %s" %isstuck)
        os.remove('%s' %filename)
        return isstuck
        
    def sendMail(self, mailContent):
        mail = Mail()
        mail.set_sender('zhangchunle@baidu.com')
        mail.set_receivers(['zhangchunle@baidu.com', 'tianshuo03@baidu.com', 'v_duchun@baidu.com', 'luotao02@baidu.com', 'zhouwei25@baidu.com', 'wanghuan29@baidu.com', 'wuhuanzhou@baidu.com'])
        mail.set_title('[告警]自动取消并rerun卡住的任务')
        mail.set_message(mailContent, messageType='html', encoding='gb2312')
        mail.send()

    def main(self):
        markRerunMessage = self.autoMarkandRerunJob()
        print(markRerunMessage)
        if markRerunMessage != '':
            mailContent = "<html><body><p>Hi, ALL:</p>  <p>以下任务被判定为运行卡住, 已自动取消，并自动rerun！</p> <p>自动rerun规则: 卡住的任务为当前commit的最新任务才会rerun, 非最新任务只会取消. </p> <table border='1' align=center> <caption><font size='3'><b>自动取消卡住的任务列表</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CIName</td><td bgcolor='#d0d0d0'>commitID</td><td bgcolor='#d0d0d0'>已运行时间/min</td><td bgcolor='#d0d0d0'>是否Rerun</td><td bgcolor='#d0d0d0'>xly链接</td></tr>"
            mailContent = mailContent + markRerunMessage
            mailContent += "</table><p>如有问题，请联系张春乐.</p> <p>张春乐</p></body></html>"
            print(mailContent)
            self.sendMail(mailContent)
            
autoRerunExceptionPR().main()