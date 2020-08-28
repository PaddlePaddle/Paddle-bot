import time
import sys
sys.path.append("..")
from utils.db import Database
from utils.mail import Mail


def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count


def timeMonitor(startTime, endTime):
    CIMonitor = {}
    for ci in [
            'PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2'
    ]:
        CIMonitor[ci] = {}
        all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName='%s' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime, endTime)
        all_commitCount = queryDB(all_commitCount_query_stat, 'count')
        CIMonitor[ci]['commitCount'] = all_commitCount
        average_wait_time_query_stat = "select mean(waitTime_total)/60 from paddle_ci_status where ciName='%s' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime, endTime)  #原因是这个时间点才有数据
        average_wait_time = queryDB(average_wait_time_query_stat, 'mean')
        CIMonitor[ci][
            'waitTime_total'] = '%.2f' % average_wait_time if average_wait_time != None else None
        average_exec_time_query_stat = "select mean(execTime_total)/60 from paddle_ci_status where ciName='%s' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime, endTime)  #原因是这个时间点才有数据
        average_exec_time = queryDB(average_exec_time_query_stat, 'mean')
        CIMonitor[ci][
            'execTime_total'] = '%.2f' % average_exec_time if average_exec_time != None else None
    return CIMonitor


def alarm(ciMontor, time_stamp):
    if time_stamp == 'before 4h':
        CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云过去4h的CI指标</b></font></caption>"
    elif time_stamp == 'before 1d':
        CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云过去1d的CI指标</b></font></caption>"
    CI_INDEX_DICT = {
        "commit个数/个": 'commitCount',
        "平均排队时间/min": 'waitTime_total',
        "平均执行时间/min": "execTime_total"
    }
    CI_NAME = "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td> "
    for ci_name in [
            'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference', 'PR-CI-CPU-Py2'
    ]:
        CI_NAME += "<td>{}</td>".format(ci_name)
    CI_NAME += "</tr>"
    CI_INDEX_INFO = ""
    for i in ['commit个数/个', '平均排队时间/min', '平均执行时间/min']:
        CI_INDEX_INFO += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
            i)
        index = CI_INDEX_DICT[i]
        for ci_name in [
                'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference',
                'PR-CI-CPU-Py2'
        ]:
            if index == 'waitTime_total' and ciMontor[ci_name][
                    index] != None and float(ciMontor[ci_name][index]) > 60:
                CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                    ciMontor[ci_name][index])
            elif index == 'execTime_total':
                if ci_name == 'PR-CI-Coverage' and ciMontor[ci_name][
                        index] != None and float(ciMontor[ci_name][
                            index]) > 110:
                    CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                        ciMontor[ci_name][index])
                elif ci_name == 'PR-CI-Py35' and ciMontor[ci_name][
                        index] != None and float(ciMontor[ci_name][
                            index]) > 60:
                    CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                        ciMontor[ci_name][index])
                elif ci_name in [
                        'PR-CI-Inference', 'PR-CI-CPU-Py2'
                ] and ciMontor[ci_name][index] != None and float(ciMontor[
                        ci_name][index]) > 20:
                    CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                        ciMontor[ci_name][index])
                else:
                    CI_INDEX_INFO += "<td>{}</td>".format(ciMontor[ci_name][
                        index])
            else:
                CI_INDEX_INFO += "<td>{}</td>".format(ciMontor[ci_name][index])
    CI_INDEX_TABLE = CI_INDEX_TITLE + CI_NAME + CI_INDEX_INFO + "</table>"
    return CI_INDEX_TABLE


def mail(HTML_CONTENT):
    mail = Mail()
    mail.set_sender('xxxx@baidu.com')
    mail.set_receivers(['xxxx@baidu.com'])
    mail.set_title('【告警】效率云过去4小时/过去1天CI指标')
    mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
    mail.send()


def regularMonitor():
    endTime = int(time.time())
    startTime = endTime - 3600 * 4
    last4hMontor = timeMonitor(startTime, endTime)
    startTime = endTime - 3600 * 24
    last1dMontor = timeMonitor(startTime, endTime)
    last4hMontor_CI_INDEX_TABLE = alarm(last4hMontor, 'before 4h')
    last1dMontor_CI_INDEX_TABLE = alarm(last1dMontor, 'before 1d')
    HTML_CONTENT = last4hMontor_CI_INDEX_TABLE + last1dMontor_CI_INDEX_TABLE
    mail(HTML_CONTENT)


regularMonitor()
