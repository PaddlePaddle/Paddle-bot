import sys
sys.path.append("..")
from utils.db import Database
from utils.mail import Mail


class continuousFailedCIMonitor():
    def __init__(self):
        self.db = Database()
        self.errorEXCODE = {
            'NetWork Not Work': 503,
            'Build Failed': 7,
            'Unknow Error': 1
        }

    def sendMail(self, receiver, title, content):
        """发送邮件"""
        mail = Mail()
        mail.set_sender('xx@baidu.com')
        mail.set_receivers(receiver)
        mail.set_title(title)
        mail.set_message(content, messageType='html', encoding='gb2312')
        mail.send()

    def errorMonitor(self):
        """
        连续失败监控
        """
        query_stat = "SELECT EXCODE,PR,commitId,ciName,targetUrl FROM paddle_ci_analysis order by time desc limit 10"
        result = list(self.db.query(query_stat))
        TABLE_CONTENT_ALL = ''
        alarm_tasks_all = []
        for key in self.errorEXCODE:
            alarm_task = []
            TABLE_CONTENT = ''
            lastesttasks_failed = []
            for record in result[0]:
                if record['EXCODE'] == self.errorEXCODE[key]:
                    netfailed_record = {}
                    netfailed_record['PR'] = record['PR']
                    netfailed_record['commitId'] = record['commitId']
                    netfailed_record['ciName'] = record['ciName']
                    netfailed_record['targetUrl'] = record['targetUrl']
                    lastesttasks_failed.append(netfailed_record)
            if len(lastesttasks_failed) > 3:
                exception_list = []
                for task in lastesttasks_failed:
                    if key != 'NetWork Not Work':
                        job = '%s_%s' % (task['PR'], task['commitId'])
                        exception_list.append(job)
                    alarm_task.append(task)
                    TABLE_CONTENT += '<tr align="center"><td> %s</td><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (
                        task['PR'], task['commitId'], task['ciName'], key,
                        task['targetUrl'])
                if key != 'NetWork Not Work':
                    if len(set(exception_list)) < 3:
                        TABLE_CONTENT = ''
                        alarm_task = []
            for alarm in alarm_task:
                alarm_tasks_all.append(alarm)
            TABLE_CONTENT_ALL += TABLE_CONTENT

        if TABLE_CONTENT_ALL != '':
            with open('../buildLog/continuousFailedCI.log', 'r') as f:
                lastalarms = f.readlines()
                f.close()
            if lastalarms[0] == str(alarm_tasks_all):
                print("The alarm content is the same as last time!")
            else:
                with open("../buildLog/continuousFailedCI.log", "w") as t:
                    t.write(str(alarm_tasks_all))
                    t.close()
                HTML_CONTENT = '<html> <head></head> <body>  <p>Hi, ALL:</p>  <p>最新的10个任务可能有以下异常，请查看是否有问题。</p> <table border="1" align="center"> <caption> <font size="3"><b>异常CI列表</b></font>  </caption> <tbody> <tr align="center"> <td bgcolor="#d0d0d0">PR</td> <td bgcolor="#d0d0d0">commitId</td><td bgcolor="#d0d0d0">ciName</td><td bgcolor="#d0d0d0">ErrorType</td><td bgcolor="#d0d0d0">xly_url</td> </tr> '
                HTML_CONTENT = HTML_CONTENT + TABLE_CONTENT_ALL + "</tbody> </table> </body></html> "
                receiver = ['xx@baidu.com']
                title = '异常导致的连续失败'
                self.sendMail(receiver, title, HTML_CONTENT)


continuousFailedCIMonitor().errorMonitor()
