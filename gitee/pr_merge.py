from gitee.handler import GiteePROperation
import json
import time
from webservice.utils.mail_163 import Mail


def gitee_merge_pr():
    """merge pr"""
    with open('Paddle-bot/gitee/commitmap.json', 'r') as f:
        data = json.load(f)
        f.close()
    merge_pr_list = []
    for key in data:
        merge_pr_list.append(key)
    merge_pr_list.sort()
    merge_pr_info = ""
    count = 0
    for PR in merge_pr_list:
        merge_status = GiteePROperation().merge('paddlepaddle', 'Paddle', PR)
        while merge_status not in [200, 201]:
            time.sleep(10)
            merge_status = GiteePROperation().merge('paddlepaddle', 'Paddle',
                                                    PR)
            count += 1
            if count >= 3:
                break
        if merge_status in [200, 201]:
            merge_pr_info = merge_pr_info + "<tr align=center><td>PR</td><td>{}</td><td>merged succeed</td></tr>".format(
                PR)
        else:
            merge_pr_info = merge_pr_info + "<tr align=center><td>PR</td><td>{}</td><td>merged failed</td></tr>".format(
                PR)

    if merge_pr_info != '':
        mail_content = "<html><body><p>Hi, ALL:</p> <p>以下gitee的PR/Issue已经被自动merge或关闭。请PM留意。</p> <table border='1' align=center> <caption><font size='3'></font></caption>"
        mail_content = mail_content + "<tr align=center><td bgcolor='#d0d0d0'>类型</td><td bgcolor='#d0d0d0'>PR/Issue号</td><td bgcolor='#d0d0d0'>状态</td></tr>" + merge_pr_info + "</table>" + "<p>如有疑问，请@张春乐。谢谢</p>" + "</body></html>"
        title = 'Gitee PR自动merge'
        receivers = ['xxxe@baidu.com', 'xxx@baidu.com', 'xxxx@baidu.com']
        sendMail(title, mail_content, receivers)


def sendMail(title, content, receivers):
    mail = Mail()
    mail.set_sender('paddlepaddle_bot@163.com')
    mail.set_receivers(receivers)
    mail.set_title(title)
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()
