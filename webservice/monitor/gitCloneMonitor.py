import json
import requests
import datetime
import time
import os
import sys
sys.path.append("..")
from utils.auth_ipipe import Get_ipipe_auth
from utils.mail import Mail

def runningJob_GitCloneTimeMonitor():
    with open("../buildLog/running_task.json", 'r') as load_f:
        all_waiting_task = json.load(load_f)
        load_f.close()
    CloneTime = []
    for task in all_waiting_task:
        targetId = task['targetId']
        commitId = task['commitId']
        CIName = task['CIName']
        if CIName.startswith('PR-CI-Py3') or CIName.startswith('PR-CI-Coverage') or CIName.startswith('PR-CI-Inference') or CIName.startswith('PR-CI-CPU-Py2'): 
            stage_url = 'https://xly.bce.baidu.com/open-api/ipipe/agile/pipeline/v1/pipelineBuild/%s' %targetId
            session, req = Get_ipipe_auth(stage_url)
            try:
                res = session.send(req).json()
            except Exception as e:
                print("Error: %s" % e)
            else:
                jobGroupBuildBeans = res['pipelineBuildBean']['stageBuildBeans'][0]['jobGroupBuildBeans'][0]
                for job in jobGroupBuildBeans:
                    jobName = job['jobName']
                    logParam = job['realJobBuild']['logUrl']
                    logUrl = "https://xly.bce.baidu.com/paddlepaddle/paddle/ibuild/auth/v2/xiaolvyun/log/downloadLog?" + logParam
                    if jobName in ['构建镜像', 'build-docker-image']:
                        stage_name = 'docker'
                    else:
                        stage_name = 'paddlebuild'
                    getIpipeBuildLog(stage_name, commitId, CIName, logUrl)
                    with open('../buildLog/%s_%s_%s.log' %(CIName, stage_name, commitId)) as f :
                        line = f.readlines()
                        #length = 10 if len(line) > 10 else len(line)
                        for i in range(0, len(line)):
                            if "Cloning into 'Paddle'..." in line[i]:
                                clone_startTime = line[i].split('Cloning')[0].strip()
                                clone_startTime = strTotimestamp(clone_startTime)
                                start_line = i
                                break
                        for i in range(start_line, len(line)):
                            if 'From https://github.com/PaddlePaddle/Paddle' in line[i]:
                                clone_endTime = line[i].split('From')[0].strip()
                                clone_endTime = strTotimestamp(clone_endTime)
                                break
                            else:
                                clone_endTime = int(time.time())
                        print("cloneTime")
                        print(clone_endTime - clone_startTime )
                        if clone_endTime - clone_startTime > 600:
                            job = {}
                            job['stage'] = stage_name
                            job['PR'] = task['PR']
                            job['CIName'] = task['CIName']
                            job['commitId'] = task['commitId']
                            job['cloneTime'] = int((clone_endTime - clone_startTime)/60)
                            CloneTime.append(job)
                        f.close()
                    os.remove("../buildLog/%s_%s_%s.log" %(CIName, stage_name, commitId))

    if len(CloneTime) != 0:
        mail_content = "<html><body><p>Hi, ALL:</p> <p>目前以下运行中的任务的gitClone时间超过10min，请注意观察代理稳定性！！</p> <table border='1' align=center> <caption><font size='3'><b>gitClone大于10min</b></font></caption>"
        mail_content = mail_content + "<tr align=center><td bgcolor='#d0d0d0'>PR</td><td bgcolor='#d0d0d0'>CI名称</td><td bgcolor='#d0d0d0'>commitId</td><td bgcolor='#d0d0d0'>阶段名称</td><td bgcolor='#d0d0d0'>gitClone时间</td></tr>"
        task_info = ""
        for task in CloneTime:
            task_info = task_info + "<tr align=center><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(task['PR'], task['CIName'], task['commitId'], task['stage'], task['cloneTime'])
        mail_content = mail_content + task_info + "</table></body></html>"
        sendMonitorMail(mail_content)

def sendMonitorMail(content):
    mail = Mail()
    mail.set_sender('zhangchunle@baidu.com')
    mail.set_receivers(['zhangchunle@baidu.com', 'tianshuo03@baidu.com', 'v_duchun@baidu.com','luotao02@baidu.com', 'wuhuanzhou@baidu.com'])
    mail.set_title('gitClone时间超过10min！')
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()

def strTotimestamp(time_str):
    d = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    t = d.timetuple()
    timeStamp = int(time.mktime(t))
    return timeStamp

def getIpipeBuildLog(typ, sha, pipelineConfName, logUrl):
    try:
        r = requests.get(logUrl)
    except Exception as e:
        print("Error: %s" % e)
    else:
        with open("../buildLog/%s_%s_%s.log" % (pipelineConfName, typ, sha), "wb") as f:
            f.write(r.content)
            f.close


runningJob_GitCloneTimeMonitor()
