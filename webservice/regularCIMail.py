from utils.readConfig import ReadConfig
from utils.mail import Mail
from utils.db import Database
from utils.convert import strTimeTotimeStamp
import datetime
import xlwt
import pandas as pd
import codecs

localConfig = ReadConfig()


def sheet_color(color):
    """set color and set center"""
    #0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray
    color_dic = {
        "Black": 0,
        "White": 1,
        "Red": 2,
        "Green": 3,
        "Blue": 4,
        "Yellow": 5,
        "Gray": 22
    }
    style = xlwt.XFStyle()
    borders = xlwt.Borders()
    pattern = xlwt.Pattern()
    alignment = xlwt.Alignment()
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    style.alignment = alignment
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN  # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
    pattern.pattern_fore_colour = color_dic[color]
    style.pattern = pattern
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    style.borders = borders
    return style


def set_center():
    """set center"""
    style = xlwt.XFStyle()
    alignment = xlwt.Alignment()
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    style.alignment = alignment
    borders = xlwt.Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    style.borders = borders
    return style


def queryCIDataWeekly(startTime, endTime):
    startTime_stamp = strTimeTotimeStamp(startTime)
    endTime_stamp = strTimeTotimeStamp(endTime)
    time_monitor_list = localConfig.cf.get('ciIndex',
                                           'time_monitor').split(',')
    other_monitor_list = localConfig.cf.get('ciIndex',
                                            'other_monitor').split(',')
    ci_index = {}
    ci_index['startTime'] = startTime.split(' ')[0]
    ci_index['endTime'] = endTime.split(' ')[0]
    ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^PR-CI/ and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
        startTime_stamp, endTime_stamp)
    ALL_commitCount = queryDB(ALL_commitCount_query_stat, 'count')
    ci_index['commitCount'] = ALL_commitCount  #一周时间效率云commit总数
    for ci in [
            'PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2'
    ]:
        average_exec_time_query_stat = "select mean(execTime_total)/60 from paddle_ci_status where ciName='%s' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime_stamp, endTime_stamp)  #原因是这个时间点才有数据
        average_exec_time = queryDB(average_exec_time_query_stat, 'mean')
        key = '%s_average_exec_time' % ci
        ci_index[key] = "%.2f" % average_exec_time
        average_wait_time_query_stat = "select mean(waitTime_total)/60 from paddle_ci_status where ciName='%s' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime_stamp, endTime_stamp)  #原因是这个时间点才有数据
        average_wait_time = queryDB(average_wait_time_query_stat, 'mean')
        key = '%s_average_wait_time' % ci
        ci_index[key] = "%.2f" % average_wait_time
        for param in time_monitor_list:
            average_value = queryStatMean(param, ci, startTime, endTime)
            key = '%s_%s' % (ci, param)
            ci_index[
                key] = "%.2f" % average_value if average_value != None else None
        for param in other_monitor_list:
            average_value = queryStatMean(
                param, ci, startTime, endTime, form='size')
            key = '%s_%s' % (ci, param)
            ci_index[
                key] = "%.2f" % average_value if average_value != None else None
        noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where ciName='%s' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime_stamp, endTime_stamp)
        noRepeat_commitCount = queryDB(noRepeat_commitCount_query_stat,
                                       'count')
        all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName='%s' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime_stamp, endTime_stamp)
        all_commitCount = queryDB(all_commitCount_query_stat, 'count')
        key = "%s_rerunRate" % ci
        ci_index[key] = "%.2f" % (1 - noRepeat_commitCount / all_commitCount)
        fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName='%s' and status='failure' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, startTime_stamp, endTime_stamp)
        fail_commitCount = queryDB(fail_commitCount_query_stat, 'count')
        key = "%s_failRate" % ci
        if fail_commitCount == None:
            ci_index[key] = 0
        else:
            ci_index[key] = "%.2f" % (fail_commitCount / all_commitCount)
    return ci_index


def queryStatMean(index, ci, startTime, endTime, form='time'):
    if form == 'size':
        query_stat = "select mean(%s) from paddle_ci_index where ciName='%s' and time > '%s' and time < '%s' and time > '2020-07-09 07:40:00'" % (
            index, ci, startTime, endTime)  #TODO time -> creatTime
    else:
        query_stat = "select mean(%s)/60 from paddle_ci_index where ciName='%s' and time > '%s' and time < '%s' and time > '2020-07-09 07:40:00'" % (
            index, ci, startTime, endTime)
    result = queryDB(query_stat, 'mean')
    return result


def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count


def keyIndicators(ci_index):
    key_ci_index = {}
    xly_average_wait_time = float(0)
    xly_average_exec_time = float(0)
    xly_average_buildTime = float(0)
    xly_average_testCaseTime_total = float(0)
    xly_average_rerunRate = float(0)
    xly_average_failRate = float(0)
    for ci in [
            'PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2'
    ]:
        key = '%s_average_wait_time' % ci
        xly_average_wait_time = xly_average_wait_time + float(ci_index[key])
        key = '%s_average_exec_time' % ci
        xly_average_exec_time = xly_average_exec_time + float(ci_index[key])
        key = '%s_buildTime' % ci
        xly_average_buildTime = xly_average_buildTime + float(ci_index[key])
        key = '%s_testCaseTime_total' % ci
        if ci_index[key] == None:
            ci_index[key] = 0
        xly_average_testCaseTime_total = xly_average_testCaseTime_total + float(
            ci_index[key])
        key = '%s_rerunRate' % ci
        xly_average_rerunRate = xly_average_rerunRate + float(ci_index[key])
        key = '%s_failRate' % ci
        xly_average_failRate = xly_average_failRate + float(ci_index[key])
    key_ci_index['xly_average_wait_time'] = "%.2f" % xly_average_wait_time
    key_ci_index['xly_average_exec_time'] = "%.2f" % xly_average_exec_time
    key_ci_index['xly_buildTime'] = "%.2f" % xly_average_buildTime
    key_ci_index[
        'xly_testCaseTime_total'] = "%.2f" % xly_average_testCaseTime_total
    key_ci_index['xly_rerunRate'] = "%.2f" % (xly_average_rerunRate / 4)
    key_ci_index['xly_failRate'] = "%.2f" % (xly_average_failRate / 4)
    return key_ci_index


def write_excel_xls(ciIndex_thisWeek, ciIndex_lastWeek=0):
    key_ci_index_thisWeek = keyIndicators(ciIndex_thisWeek)
    key_ci_index_lastWeek = keyIndicators(
        ciIndex_lastWeek) if ciIndex_lastWeek != 0 else None
    workbook = xlwt.Workbook(encoding='utf-8')
    startTime = ciIndex_thisWeek['startTime']
    endTime = ciIndex_thisWeek['endTime']
    worksheet = workbook.add_sheet('%s~%s' % (startTime, endTime))
    worksheet.col(0).width = 8888
    for i in range(1, 6):
        worksheet.col(i).width = 5555
    worksheet.write(0, 0, "效率云%s~%s CI关键指标" % (startTime, endTime),
                    sheet_color("Yellow"))
    worksheet.write(1, 0, "CI名称", sheet_color("Gray"))
    worksheet.write(2, 0, "平均排队时间/min", sheet_color("Gray"))
    worksheet.write(3, 0, "平均执行时间/min", sheet_color("Gray"))
    worksheet.write(4, 0, "平均编译时间/min", sheet_color("Gray"))
    worksheet.write(5, 0, "平均单测时间/min", sheet_color("Gray"))
    worksheet.write(6, 0, "平均rerun率", sheet_color("Gray"))
    worksheet.write(7, 0, "平均失败率", sheet_color("Gray"))
    KEY_CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云对内关键指标</b></font></caption>"  #%(startTime, endTime)
    key_ci_index_dic = {
        "平均排队时间/min": "xly_average_wait_time",
        "平均执行时间/min": "xly_average_exec_time",
        "平均编译时间/min": "xly_buildTime",
        "平均单测时间/min": "xly_testCaseTime_total",
        "平均rerun率": "xly_rerunRate",
        "平均失败率": "xly_failRate"
    }
    CI_NAME = "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td> "
    col = 1
    for ci_name in [
            '汇总', 'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference',
            'PR-CI-CPU-Py2'
    ]:
        worksheet.write(1, col, ci_name, set_center())
        CI_NAME += "<td>{}</td>".format(ci_name)
        col += 1
    CI_NAME += "</tr>"  #正文表格第一行构造完成
    KEY_CI_INDEX_INFO = ""
    line = 2
    for i in [
            '平均排队时间/min', '平均执行时间/min', '平均编译时间/min', '平均单测时间/min', '平均rerun率',
            '平均失败率'
    ]:
        KEY_CI_INDEX_INFO += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
            i)
        col = 1
        for ci_name in [
                '汇总', 'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference',
                'PR-CI-CPU-Py2'
        ]:
            if i == '平均单测时间/min' and ci_name in [
                    'PR-CI-Inference', 'PR-CI-CPU-Py2'
            ]:
                worksheet.write(line, col, 'None', set_center())
                KEY_CI_INDEX_INFO += "<td>None</td>"
            else:
                #只产出本周数据
                if ciIndex_lastWeek == 0:
                    if ci_name == "汇总":
                        key = key_ci_index_dic[i]
                        worksheet.write(line, col, key_ci_index_thisWeek[key],
                                        set_center())
                        KEY_CI_INDEX_INFO += "<td>{}</td>".format(
                            key_ci_index_thisWeek[key])
                    else:
                        key = key_ci_index_dic[i].replace('xly', ci_name)
                        worksheet.write(line, col, ciIndex_thisWeek[key],
                                        set_center())
                        KEY_CI_INDEX_INFO += "<td>{}</td>".format(
                            ciIndex_thisWeek[key])
                #产出与上周对比数据
                else:
                    if ci_name == "汇总":
                        key = key_ci_index_dic[i]
                        thisWeek_lastWeek_radio = float(
                            (float(key_ci_index_thisWeek[key]) -
                             float(key_ci_index_lastWeek[key])) /
                            float(key_ci_index_lastWeek[key])
                        ) if key_ci_index_lastWeek[key] != 0 else float(
                            (float(key_ci_index_thisWeek[key]) - 0.00001
                             )) / 0.00001
                        value = '%s' % key_ci_index_thisWeek[key]
                    else:
                        key = key_ci_index_dic[i].replace('xly', ci_name)
                        thisWeek_lastWeek_radio = float(
                            (float(ciIndex_thisWeek[key]) -
                             float(ciIndex_lastWeek[key])) /
                            float(ciIndex_lastWeek[key])) if ciIndex_lastWeek[
                                key] != 0 else float(
                                    (float(ciIndex_thisWeek[key]) - 0.00001
                                     )) / 0.00001
                        value = '%s' % ciIndex_thisWeek[key]
                    if thisWeek_lastWeek_radio >= 0:
                        value = value + ' (↑ %.2f' % (thisWeek_lastWeek_radio *
                                                      100) + '%)'
                        if thisWeek_lastWeek_radio >= 0.05:
                            worksheet.write(line, col, value,
                                            sheet_color("Red"))
                            KEY_CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                                value)
                        else:
                            worksheet.write(line, col, value, set_center())
                            KEY_CI_INDEX_INFO += "<td>{}</td>".format(value)
                    elif thisWeek_lastWeek_radio < 0:
                        value = value + '(↓ %.2f' % (
                            abs(thisWeek_lastWeek_radio) * 100) + '%)'
                        if thisWeek_lastWeek_radio <= -0.05:
                            worksheet.write(line, col, value,
                                            sheet_color("Green"))
                            KEY_CI_INDEX_INFO += "<td bgcolor='#b5c4b1'>{}</td>".format(
                                value)
                        else:
                            worksheet.write(line, col, value, set_center())
                            KEY_CI_INDEX_INFO += "<td>{}</td>".format(value)
            col += 1
        line += 1
        KEY_CI_INDEX_INFO += "</tr>"
    First_Table = KEY_CI_INDEX_TITLE + CI_NAME + KEY_CI_INDEX_INFO + "</table>"  #第一个表格主要存放与上周对比的关键数据

    worksheet.write(9, 0, "效率云本周各CI评价指标详情", sheet_color("Yellow"))
    THISWEEK_CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云对内详细指标</b></font></caption>"
    ci_index_dic = {"00平均排队时间/min": "ci_average_wait_time", "01平均执行时间/min": "ci_average_exec_time", "02平均编译时间/min": "ci_buildTime", "03平均单测时间/min": "ci_testCaseTime_total",\
        "04平均测试预测库时间/min": "ci_testFluidLibTime", \
        "05平均测试训练库时间/min": "ci_testFluidLibTrainTime", "06平均预测库大小/M": "ci_fluidInferenceSize", "07平均whl大小/M": "ci_WhlSize", \
        "08平均build目录大小/G": "ci_buildSize", "09单测总数/个": "ci_testCaseCount_total", "10单卡case总数/个": "ci_testCaseCount_single", \
        "11单卡case执行时间/min": "ci_testCaseTime_single", "12多卡case总数/个": "ci_testCaseCount_multi", "13多卡case执行时间/min": "ci_testCaseTime_multi", \
        "14独占case总数/个": "ci_testCaseCount_exclusive", "15独占case执行时间/min": "ci_testCaseTime_exclusive", "16平均失败率": "ci_failRate", \
        "17平均rerun率": "ci_rerunRate"}
    ci_index_key_list = sorted(ci_index_dic.keys())
    col = 1
    worksheet.write(10, 0, "CI名称", sheet_color("Gray"))
    THISWEEK_CI_INDEX_First_LINE = "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
    for ci_name in [
            'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference', 'PR-CI-CPU-Py2'
    ]:
        worksheet.write(10, col, ci_name, sheet_color("Gray"))
        THISWEEK_CI_INDEX_First_LINE += "<td>{}</td>".format(ci_name)
        col += 1
    THISWEEK_CI_INDEX_First_LINE += "</tr>"
    THISWEEK_CI_INDEX_INFO = ""
    col = 1
    for i in range(len(ci_index_dic)):
        key = ci_index_key_list[i][2:]
        worksheet.write(11 + i, 0, key, sheet_color("Gray"))
        THISWEEK_CI_INDEX_INFO += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
            key)
        col = 1
        for ci_name in [
                'PR-CI-Coverage', 'PR-CI-Py35', 'PR-CI-Inference',
                'PR-CI-CPU-Py2'
        ]:
            if key == '平均单测时间/min' and ci_name in [
                    'PR-CI-Inference', 'PR-CI-CPU-Py2'
            ]:
                worksheet.write(11 + i, col, 'None', set_center())
                THISWEEK_CI_INDEX_INFO += "<td>None</td>"
            else:
                key = ci_index_dic[ci_index_key_list[i]].replace('ci', ci_name)
                worksheet.write(11 + i, col, ciIndex_thisWeek[key],
                                set_center())
                if ciIndex_thisWeek[key] == None or ciIndex_thisWeek[
                        key] == "":
                    THISWEEK_CI_INDEX_INFO += "<td class='first'></td>"
                else:
                    THISWEEK_CI_INDEX_INFO += "<td>{}</td>".format(
                        ciIndex_thisWeek[key])
            col += 1
        THISWEEK_CI_INDEX_INFO += "</tr>"
    SENCOND_TABLE = THISWEEK_CI_INDEX_TITLE + THISWEEK_CI_INDEX_First_LINE + THISWEEK_CI_INDEX_INFO + "</table>"
    HTML_TABLE_CONTENT = First_Table + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" + SENCOND_TABLE  #第二个表格本周数据
    workbook.save('ciIndexData/ci_index%s.xls' % endTime)
    return HTML_TABLE_CONTENT


def sendMail(ciIndex_thisWeek, ciIndex_lastWeek=0):
    thisWeekCommit = ciIndex_thisWeek['commitCount']
    lastWeekCommit = ciIndex_lastWeek[
        'commitCount'] if ciIndex_lastWeek != 0 else 0
    COMMIT_AND_TIME = "<table border='1' align=center> <caption><font size='3'><b>用户感知指标</b></font></caption>"
    if ciIndex_lastWeek == 0:
        DIFF_RATE = "%.2f" % float((thisWeekCommit - 0.00001) / 0.00001 * 100)
    else:
        DIFF_RATE = "%.2f" % float(
            abs(thisWeekCommit - lastWeekCommit) / lastWeekCommit * 100)
    if thisWeekCommit - lastWeekCommit > 0:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit数</td><td bgcolor='#ff6eb4'>%s(↑ %s" % (
            thisWeekCommit, DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"
    else:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit数</td><td bgcolor='#b5c4b1'>%s(↓ %s" % (
            thisWeekCommit, DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"
    MAX_WAITTIME = max(
        float(ciIndex_thisWeek['PR-CI-Coverage_average_wait_time']),
        float(ciIndex_thisWeek['PR-CI-Py35_average_wait_time']),
        float(ciIndex_thisWeek['PR-CI-Inference_average_wait_time']),
        float(ciIndex_thisWeek['PR-CI-CPU-Py2_average_wait_time']))
    MAX_EXECTIME = max(
        float(ciIndex_thisWeek['PR-CI-Coverage_average_exec_time']),
        float(ciIndex_thisWeek['PR-CI-Py35_average_exec_time']),
        float(ciIndex_thisWeek['PR-CI-Inference_average_exec_time']),
        float(ciIndex_thisWeek['PR-CI-CPU-Py2_average_exec_time']))
    COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit从提交到返回结果耗时</td><td>%.2f min</td></tr>" % (
        MAX_WAITTIME + MAX_EXECTIME)
    COMMIT_AND_TIME += "</table>"
    HTML_CONTENT = "<html><body><p>Hi, ALL:</p> <p>本周CI评价指标详细信息可参考如下表格:</p> %s" % COMMIT_AND_TIME
    HTML_TABLE_CONTENT = write_excel_xls(ciIndex_thisWeek, ciIndex_lastWeek)
    HTML_CONTENT = HTML_CONTENT + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" + HTML_TABLE_CONTENT + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" + "<p>如有问题，随时联系</p> <p>张春乐</p></body></html>"
    mail = Mail()
    mail.set_sender('xxxx@xxxx.com')
    mail.set_receivers(['xxxx@xxxx.com', 'xxxx@xxxx.com'])
    mail.set_title('效率云%s~%s CI评价指标统计' % (ciIndex_thisWeek['startTime'],
                                          ciIndex_thisWeek['endTime']))
    mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
    mail.send()


def main():
    ciIndex_thisWeek = queryCIDataWeekly('2020-07-13 00:00:00',
                                         '2020-07-17 00:00:00')
    ciIndex_lastWeek = queryCIDataWeekly('2020-07-07 00:00:00',
                                         '2020-07-13 00:00:00')
    sendMail(ciIndex_thisWeek, ciIndex_lastWeek)


main()
