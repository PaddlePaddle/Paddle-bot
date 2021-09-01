import sys
import json
import requests
import datetime
sys.path.append("..")
from utils.mail import Mail
from utils.db import Database
from utils.handler import PRHandler, xlyHandler


class ErrorIpipJob(xlyHandler, PRHandler):


    def __init__(self):
        self.db = Database()
        self.container_ci = {
            'xxx@baidu.com': {
                '14603': 'Build-cpu-mkl',
                '14602': 'Build-cuda110-cudnn7-mkl-gcc82',
                '13228': 'Build-cuda101-cudnn7-mkl-gcc82',
                '14607': 'Build-cuda102-cudnn7-mkl-gcc82',
                '14608': 'Build-cpu-openblas',
                '14611': 'Build-cpu-noavx-openblas',
                '14621': 'Build-cuda102-cudnn8-mkl-gcc82',
                '19133': 'Build-cuda112-cudnn8-mkl-gcc82',
                '15568': 'Build-Mac-Python3',
                },
            'xxx@baidu.com': {
                '15107': 'Build-windows-cuda101-cudnn7-mkl',
                '15108': 'Build-windows-cuda102-cudnn7-mkl',
                '18421': 'Build-windows-cuda112-cudnn8-mkl',
                '18505': 'Build-windows-cpu-noavx-mkl',
                '18506': 'Build-windows-cpu-noavx-open',
                '18507': 'Build-windows-cpu-avx-open',
                '14996': 'Build-windows-cpu-avx-mkl',
                '18509': 'Build-windows-cuda102-cudnn7-noavx-mkl',
                '18510': 'Build-windows-cuda101-cudnn7-noavx-mkl',
                '18597': 'Build-windows-cuda110-cudnn8-mkl',
                },
            'xxx@baidu.com': {
                '18996': 'Build-ROCm401-MIOpen211-MKL',
                },
        }

    def time_check(self, job_log):
        message_error = ''
        now_time = datetime.datetime.now().strftime('%Y-%m-%d')
        log_time = job_log[0]['buildTime']/1000
        dateArray = datetime.datetime.fromtimestamp(log_time)
        log_time = dateArray.strftime('%Y-%m-%d')

        if log_time != now_time:
            message_error = "time is old, logtime is %s, but today is %s" %(log_time,now_time)
        return message_error


    def status_check(self, job_log):
        message_error = ''
        log_status = job_log[0]['status']
        if log_status != 'SUCC':
            message_error = "log status is not success, please check log"
        return message_error


    def jobStatus(self):
        message_error = ''
        email_list = ['xxx@baidu.com', 'xxx@baidu.com']
        for email_name,ci_dic in self.container_ci.items():
            for job_id in ci_dic:
                url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/ipipe/rest/v3/pipeline-builds?_embed[]=trigger&_embed[]=stageBuilds&_include[]=ext.indexOfStageWithCompileBuild&_include[]=stageBuilds.ext.releaseVersion&_limit=1&_offset=0&branch=develop&pipelineConfId=' + job_id
                response = requests.get(url).text
                job_log = json.loads(response)
                time_error_log = self.time_check(job_log)
                status_error_log = self.status_check(job_log)
                job_name = ci_dic[job_id]
                log_url = 'https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/%s/job/%s' %(job_log[0]['id'], job_log[0]['headJob'])
                if status_error_log != '':
                    email_list.append(email_name)
                    if message_error == '':
                        message_error = job_name + ' ' + time_error_log + ' ' + status_error_log + ' ' + log_url + '<br />'
                    else:
                        message_error = message_error + job_name + ' ' + time_error_log + ' ' + status_error_log + ' ' + log_url + '<br />'
        if message_error != '':
            email_list = list(set(email_list))
            self.sendMonitorMail(message_error, email_list)


    def sendMonitorMail(self, content, email_list):
        mail = Mail()
        mail.set_sender('xxx@baidu.com')
        mail.set_receivers(email_list)
        mail.set_title('Night-Build-CI')
        mail.set_message(content, messageType='html', encoding='gb2312')
        mail.send()


ErrorIpipJob().jobStatus()
