import requests
import json
import time
import os
import sys
sys.path.append("..")
from utils.mail_163 import Mail


class PaddleBotMonitor(object):
    """
    Paddle-bot自身的监控
    1. 检查status状态
    2. 发送Post请求
    3. 再次检查status状态
    """

    def __init__(self):
        self.checkrun_api = 'https://api.github.com/repos/lelelelelez/paddle-bot-test/check-runs/{check_run_id}'
        self.checksuit_api = 'https://api.github.com/repos/lelelelelez/paddle-bot-test/check-suites/7270836943/check-runs'  #7270836943 为checksuit id  
        self.updatepr_api = 'https://api.github.com/repos/lelelelelez/paddle-bot-test/pulls/{pull_number}'

    def checkCIStatus(self):
        response = requests.get(self.checksuit_api).json()
        print(response)
        status = response['check_runs'][0]['conclusion']
        return status

    def updatePR(self, message):
        headers = {
            'authorization': "token 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",
            "accept": "application/vnd.github.v3+json",
            'content-type': "application/json"
        }
        data = {"body": message}
        update_url = self.updatepr_api.format(pull_number=96)
        response = requests.patch(
            update_url, data=json.dumps(data), headers=headers)
        print("updatePR: %s" % response)

    def monitor(self):
        """
        1. 第一次正常更新PR描述来检查服务是否正常
        2. 服务不正常
            2.1 重启服务
            2.2 根据首次监测到的PR描述状态来进一步判断是下一步操作是怎样
        """
        checkPRStatus = self.checkCIStatus()
        print("96 first status: %s " % checkPRStatus)

        if checkPRStatus == 'failure':
            self.updatePR('update pr descripotion')
        elif checkPRStatus == 'success':
            self.updatePR('')
        else:
            self.updatePR('pending fix%s' % int(time.time()))
        time.sleep(30)
        re_checkCIStatus = self.checkCIStatus()
        if re_checkCIStatus == None:
            time.sleep(10)
            re_checkCIStatus = self.checkCIStatus()
        print("96 second status: %s " % re_checkCIStatus)
        count = 1
        while count < 6 and re_checkCIStatus == checkPRStatus:
            os.system('sh restartSmee.sh')
            if checkPRStatus == 'failure':
                self.updatePR('update pr descripotion %s' % count)
            elif checkPRStatus == 'success':
                self.updatePR('%s' % count)
                time.sleep(30)
                self.updatePR('')
            time.sleep(30)
            re_checkCIStatus = self.checkCIStatus()
            print("restart smee  96 status: %s " % re_checkCIStatus)
            print("restart count: %s" % count)
            count += 1
        if count != 1:
            restart_log = '%s Paddle-bot restart %s' % (time.strftime(
                "%Y%m%d %H:%M:%S", time.localtime()), count)
            restartBot_record = 'restartBot.txt'
            with open(restartBot_record, 'a+') as f:
                f.write(restart_log + '\n')
            f.close()
        if count == 6 and re_checkCIStatus == checkPRStatus:
            self.sendMail('Paddle-bot服务不稳定, 请即时查看')
            print("Paddle-bot服务不稳定!")
        else:
            print("Paddle-bot server is ok!")

    def sendMail(self, mailContent):
        mail = Mail()
        mail.set_sender('paddlepaddle_bot@163.com')
        mail.set_receivers(['xxx@baidu.com'])
        mail.set_title('Paddle-bot服务不稳定')
        mail.set_message(mailContent, messageType='html', encoding='gb2312')
        mail.send()


PaddleBotMonitor().monitor()
