# import sys
# sys.path.append("/home/jiangxinzhou01/test/Paddle-bot/")
from gitee.handler import GiteePROperation

import json
import time
from webservice.utils.mail_163 import Mail
from Singleton import MySingleton


def gitee_merge_pr():
    """merge pr"""
    merge_pr_list = GiteePROperation().getPRListWithOpenStatus('paddlepaddle',
                                                               'Paddle')
    merge_pr_list.sort()
    print(merge_pr_list)
    merge_pr_info = ""
    count = 0
    singleton = MySingleton()
    for PR in merge_pr_list:
        print("PR: %s" % PR)
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
            pr_state = singleton.get_github_pr_by_gitee_pr(PR)
            singleton.set_pr_merge_state(pr_state.github_pr, '已合入')
        else:
            merge_pr_info = merge_pr_info + "<tr align=center><td>PR</td><td>{}</td><td>merged failed</td></tr>".format(
                PR)
    # if merge_pr_info != '':
    #     mail_content = "<html><body><p>Hi, ALL:</p> <p>以下gitee的PR/Issue已经被自动merge或关闭。请PM留意。</p> <table border='1' align=center> <caption><font size='3'></font></caption>"
    #     mail_content = mail_content + "<tr align=center><td bgcolor='#d0d0d0'>类型</td><td bgcolor='#d0d0d0'>PR/Issue号</td><td bgcolor='#d0d0d0'>状态</td></tr>" + merge_pr_info + "</table>" + "<p>如有疑问，请@张春乐。谢谢</p>" + "</body></html>"
    #     title = 'Gitee PR自动merge'
    #     receivers = ['zhangchunle@baidu.com', 'v_duchun@baidu.com', 'sunwanting01@baidu.com', 'jiangxinzhou01@baidu.com']
    #     sendMail(title, mail_content, receivers)


def sendMail(title, content, receivers):
    mail = Mail()
    mail.set_sender('paddlepaddle_bot@163.com')
    mail.set_receivers(receivers)
    mail.set_title(title)
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()


# gitee_merge_pr()
