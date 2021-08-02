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


def sendMail(title, content, receivers):
    mail = Mail()
    mail.set_sender('xxxxx@163.com')
    mail.set_receivers(receivers)
    mail.set_title(title)
    mail.set_message(content, messageType='html', encoding='gb2312')
    mail.send()


# gitee_merge_pr()
