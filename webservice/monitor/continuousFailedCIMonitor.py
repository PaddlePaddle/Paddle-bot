import sys
sys.path.append("..")
from utils.db import Database
from utils.mail import Mail

class continuousFailedCIMonitor():
    def __init__(self):
        self.db = Database()
        self.errorEXCODE = {'NetWork Not Work': 503, 'Build Failed': 7, 'Unknow Error': 1}

    def sendMail(self, receiver, title, content):
        """发送邮件"""
        mail = Mail()
        mail.set_sender('zhangchunle@baidu.com')
        mail.set_receivers(receiver)
        mail.set_title(title)
        mail.set_message(content, messageType='html', encoding='gb2312')
        mail.send()
    '''
    def errorMonitor(self):
        """
        连续失败监控
        """
        query_stat = "SELECT EXCODE,PR,commitId,ciName FROM paddle_ci_index order by time desc limit 10"
        result = list(self.db.query(query_stat))
        print("result: %s" %result)
        TABLE_CONTENT = ''
        #for key in self.errorEXCODE:
        lastesttasks_failed = []
        netfailed_record = {}
        for record in result[0]:
            print("record: ")
            print(record)
            if record['EXCODE'] in self.errorEXCODE.values():
                job = '%s_%s_%s' %(record['PR'], record['commitId'], record['EXCODE'])
                if record['EXCODE'] == 503:
                    netfailed_record[job] = record['ciName']
                    lastesttasks_failed.append(netfailed_record)
                else:

                    if job not in netfailed_record:
                        netfailed_record[job] = []
                        netfailed_record[job].append(record['ciName'])
                    else:
                        netfailed_record[job].append(record['ciName'])
                    #job = '%s_%s' %(record['PR'], record['commitId'])
                    #netfailed_record['ciName'] = []
                    #netfailed_record['ciName'].append(record['ciName'])
                    lastesttasks_failed.append(netfailed_record)
        print(" %s" %(lastesttasks_failed))   
            #if len(lastesttasks_failed) > 3:
            #    for task in lastesttasks_failed:
            #        TABLE_CONTENT += '<tr align="center" bgcolor="#b5c4b1"><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' %(task['PR'], task['commitId'], task['ciName'], key)
            #print("%s: %s" %(key, lastesttasks_failed))
    
        if TABLE_CONTENT != '':
            HTML_CONTENT = '<html> <head></head> <body>  <p>Hi, ALL:</p>  <p>最新的10个任务可能有以下异常，请查看是否有问题。</p><table border="1" align="center"> <caption> <font size="3"><b>异常CI列表</b></font>  </caption> <tbody> <tr align="center"> <td bgcolor="#d0d0d0">PR</td> <td bgcolor="#d0d0d0">commitId</td><td bgcolor="#d0d0d0">ciName</td><td bgcolor="#d0d0d0">ErrorType</td> </tr> '
            HTML_CONTENT = HTML_CONTENT + TABLE_CONTENT + "</tbody> </table> </body></html> "
            print(HTML_CONTENT)
            receiver = ['zhangchunle@baidu.com']#, 'tianshuo03@baidu.com', 'v_duchun@baidu.com', 'wuhuanzhou@baidu.com', 'luotao02@baidu.com']
            title =  '异常导致的连续失败'
            self.sendMail(receiver, title, HTML_CONTENT)  
        
    '''
    def errorMonitor(self):
        """
        连续失败监控
        """
        query_stat = "SELECT EXCODE,PR,commitId,ciName FROM paddle_ci_index order by time desc limit 10"
        result = list(self.db.query(query_stat))
        print("result: %s" % result)
        TABLE_CONTENT = ''
        for key in self.errorEXCODE:
            lastesttasks_failed = []
            for record in result[0]:
                if record['EXCODE'] == self.errorEXCODE[key] and record['PR'] not in [31226, 31292]:
                    netfailed_record = {}
                    netfailed_record['PR'] = record['PR']
                    netfailed_record['commitId'] = record['commitId']
                    netfailed_record['ciName'] = record['ciName']
                    lastesttasks_failed.append(netfailed_record)
            if len(lastesttasks_failed) > 3:
                for task in lastesttasks_failed:
                    TABLE_CONTENT += '<tr align="center" bgcolor="#b5c4b1"><td> %s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (
                        task['PR'], task['commitId'], task['ciName'], key)
            print("%s: %s" % (key, lastesttasks_failed))
        print(TABLE_CONTENT)
        
        if TABLE_CONTENT != '':
            HTML_CONTENT = '<html> <head></head> <body>  <p>Hi, ALL:</p>  <p>最新的10个任务可能有以下异常，请查看是否有问题。</p> <table border="1" align="center"> <caption> <font size="3"><b>异常CI列表</b></font>  </caption> <tbody> <tr align="center"> <td bgcolor="#d0d0d0">PR</td> <td bgcolor="#d0d0d0">commitId</td><td bgcolor="#d0d0d0">ciName</td><td bgcolor="#d0d0d0">ErrorType</td> </tr> '
            HTML_CONTENT = HTML_CONTENT + TABLE_CONTENT + "</tbody> </table> </body></html> "
            receiver = ['zhangchunle@baidu.com', 'zhouwei25@baidu.com', 'tianshuo03']
            title = '异常导致的连续失败'
            self.sendMail(receiver, title, HTML_CONTENT)
        
continuousFailedCIMonitor().errorMonitor()
