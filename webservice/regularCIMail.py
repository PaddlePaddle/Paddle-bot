from utils.readConfig import ReadConfig
from utils.mail import Mail
from utils.db import Database
from utils.convert import strTimeTotimeStamp
import datetime
import codecs

localConfig = ReadConfig()


def queryCIDataWeekly(startTime, endTime):
    startTime_stamp = strTimeTotimeStamp(startTime)
    endTime_stamp = strTimeTotimeStamp(endTime)
    time_monitor_list = localConfig.cf.get('ciIndex',
                                           'time_monitor').split(',')
    other_monitor_list = localConfig.cf.get('ciIndex',
                                            'other_monitor').split(',')
    CI_NAME_list = localConfig.cf.get('ciIndex', 'ci_name').split(',')  #所有的ci
    ci_index = {}
    ci_index['startTime'] = startTime.split(' ')[0]
    ci_index['endTime'] = endTime.split(' ')[0]
    #commit数目按repo来分
    repo_list = localConfig.cf.get('ciIndex', 'commitCount').split(',')
    for repo in repo_list:
        key = '%s_commitCount' % repo.split('/')[1]
        ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where repo='%s' and commit_createTime > %s and commit_createTime < %s" % (
            repo, startTime_stamp, endTime_stamp)
        ALL_commitCount = queryDB(ALL_commitCount_query_stat, 'count')
        ci_index[key] = ALL_commitCount

    for ci in ['PR-CI-Windows-OPENBLAS']:  #CI_NAME_list: 
        print(ci)
        if ci == 'PR-CI-Mac':
            queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/' % ci
        elif ci == 'PR-CI-Windows':
            queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/' % ci
        else:
            queryCIName = 'ciName =~ /^%s/' % ci
        average_exec_time_query_stat = "select mean(execTime_total)/60 from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            queryCIName, startTime_stamp, endTime_stamp)  #原因是这个时间点才有数据
        print(average_exec_time_query_stat)
        average_wait_time_query_stat = "select mean(waitTime_total)/60 from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            queryCIName, startTime_stamp, endTime_stamp)  #原因是这个时间点才有数据
        average_exec_time = queryDB(average_exec_time_query_stat, 'mean')
        key = '%s_average_exec_time' % ci
        ci_index[
            key] = "%.2f" % average_exec_time if average_exec_time != None else None
        average_wait_time = queryDB(average_wait_time_query_stat, 'mean')
        key = '%s_average_wait_time' % ci
        ci_index[
            key] = "%.2f" % average_wait_time if average_wait_time != None else None
        key = '%s_average_consum_time' % ci
        ci_index[key] = "%.2f" % (
            average_wait_time + average_exec_time
        ) if average_wait_time != None or average_exec_time != None else None
        #average_dockerbuild_time_query_stat = "select mean(docker_build_endTime - docker_build_startTime)/60 from paddle_ci_status where ciName='%s' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (ci, startTime_stamp, endTime_stamp)
        #select mean(t)/60 from (select docker_build_endTime - docker_build_startTime as t from paddle_ci_status where ciName='PR-CI-Py3' and commit_createTime >1597593600  and commit_createTime <1598198400 and time > '2020-07-09 07:40:00')
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

        noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            queryCIName, startTime_stamp, endTime_stamp)
        noRepeat_commitCount = queryDB(noRepeat_commitCount_query_stat,
                                       'count')
        all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            queryCIName, startTime_stamp, endTime_stamp)
        all_commitCount = queryDB(all_commitCount_query_stat, 'count')
        key = "%s_rerunRate" % ci
        ci_index[key] = "%.2f" % (1 - noRepeat_commitCount / all_commitCount)
        fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and status='failure' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
            queryCIName, startTime_stamp, endTime_stamp)
        fail_commitCount = queryDB(fail_commitCount_query_stat, 'count')
        key = "%s_failRate" % ci
        if fail_commitCount == None:
            ci_index[key] = 0
        else:
            ci_index[key] = "%.2f" % (fail_commitCount / all_commitCount)
    #获取commit耗时最长时间
    longest_time_query_stat = 'SELECT MAX(t) from (SELECT waitTime_total+execTime_total as t from paddle_ci_status  where commit_createTime > %s and commit_createTime < %s)' % (
        startTime_stamp, endTime_stamp)
    longest_time = queryDB(longest_time_query_stat, 'max')
    ci_index['LongestTime'] = '%.2f' % float(longest_time / 60)
    print(ci_index)
    return ci_index


def queryStatMean(index, ci, startTime, endTime, form='time'):
    if ci == 'PR-CI-Mac':
        queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/' % ci
    elif ci == 'PR-CI-Windows':
        queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/' % ci
    else:
        queryCIName = 'ciName =~ /^%s/' % ci
    if form == 'size':
        query_stat = "select mean(%s) from paddle_ci_index where %s and time > '%s' and time < '%s' " % (
            index, queryCIName, startTime, endTime)  #TODO time -> creatTime
    else:
        query_stat = "select mean(%s)/60 from paddle_ci_index where %s and time > '%s' and time < '%s'" % (
            index, queryCIName, startTime, endTime)
    print(query_stat)
    result = queryDB(query_stat, 'mean')
    print(result)
    return result


def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count


def get_key_detail_ci_index(ciIndex_thisWeek, ciIndex_lastWeek=0):
    startTime = ciIndex_thisWeek['startTime']
    endTime = ciIndex_thisWeek['endTime']
    CI_NAME_list = localConfig.cf.get('ciIndex', 'ci_name').split(',')  #所有的ci

    #对内关键指标
    KEY_CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云对内关键指标</b></font></caption>"  #%(startTime, endTime)
    key_ci_index_dic = {
        "平均耗时/min": "xly_average_consum_time",
        "平均排队时间/min": "xly_average_wait_time",
        "平均执行时间/min": "xly_average_exec_time",
        "平均构建镜像时间/min": "xly_average_docker_time",
        "平均编译时间/min": "xly_buildTime",
        "平均单测时间/min": "xly_testCaseTime_total",
        "平均rerun率": "xly_rerunRate",
        "平均失败率": "xly_failRate"
    }
    CI_NAME = "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td> "
    for ci_name in CI_NAME_list:
        CI_NAME += "<td>{}</td>".format(ci_name)
    CI_NAME += "</tr>"  #正文表格第一行构造完成
    KEY_CI_INDEX_INFO = ""
    for i in [
            '平均耗时/min', '平均排队时间/min', '平均执行时间/min', '平均编译时间/min', '平均单测时间/min',
            '平均rerun率', '平均失败率'
    ]:
        KEY_CI_INDEX_INFO += "<tr align=center><td bgcolor='#d0d0d0'>{}(本周值|上周值|浮动)</td>".format(
            i)
        for ci_name in CI_NAME_list:
            if ci_name in ['FluidDoc1'] and i in ['平均编译时间/min', '平均单测时间/min']:
                KEY_CI_INDEX_INFO += "<td>None</td>"
            elif i == '平均单测时间/min' and ci_name in [
                    'PR-CI-Inference', 'PR-CI-CPU-Py2',
                    'PR-CI-Windows-OPENBLAS'
            ]:
                KEY_CI_INDEX_INFO += "<td>None</td>"
            else:
                #只产出本周数据
                if ciIndex_lastWeek == 0:
                    key = key_ci_index_dic[i].replace('xly', ci_name)
                    KEY_CI_INDEX_INFO += "<td>{}</td>".format(ciIndex_thisWeek[
                        key])
                #产出与上周对比数据
                else:
                    key = key_ci_index_dic[i].replace('xly', ci_name)
                    if i in ['平均rerun率', '平均失败率']:
                        # 这俩参数已经是百分率了
                        thisWeek_lastWeek_radio = float(ciIndex_thisWeek[
                            key]) - float(ciIndex_lastWeek[key])
                    else:
                        thisWeek_lastWeek_radio = float(
                            (float(ciIndex_thisWeek[key]) -
                             float(ciIndex_lastWeek[key])) /
                            float(ciIndex_lastWeek[key])) if ciIndex_lastWeek[
                                key] != 0 else float(
                                    (float(ciIndex_thisWeek[key]) - 0.00001
                                     )) / 0.00001
                    value = '%s | %s' % (ciIndex_thisWeek[key],
                                         ciIndex_lastWeek[key])
                    if thisWeek_lastWeek_radio >= 0:
                        value = value + ' |↑%.2f' % (thisWeek_lastWeek_radio *
                                                     100) + '%'
                        if thisWeek_lastWeek_radio >= 0.05:
                            KEY_CI_INDEX_INFO += "<td bgcolor='#ff6eb4'>{}</td>".format(
                                value)
                        else:
                            KEY_CI_INDEX_INFO += "<td>{}</td>".format(value)
                    elif thisWeek_lastWeek_radio < 0:
                        value = value + ' |↓%.2f' % (
                            abs(thisWeek_lastWeek_radio) * 100) + '%'
                        if thisWeek_lastWeek_radio <= -0.05:
                            KEY_CI_INDEX_INFO += "<td bgcolor='#b5c4b1'>{}</td>".format(
                                value)
                        else:
                            KEY_CI_INDEX_INFO += "<td>{}</td>".format(value)
        KEY_CI_INDEX_INFO += "</tr>"
    KEY_CI_INDEX_TABLE = KEY_CI_INDEX_TITLE + CI_NAME + KEY_CI_INDEX_INFO + "</table>"  #第一个表格主要存放与上周对比的关键数据

    #本周详细指标
    THISWEEK_CI_INDEX_TITLE = "<table border='1' align=center> <caption><font size='3'><b>效率云对内详细指标</b></font></caption>"
    ci_index_dic = {"00平均耗时/min": "ci_average_consum_time", "01平均排队时间/min": "ci_average_wait_time", "02平均执行时间/min": "ci_average_exec_time", \
        "03平均编译时间/min": "ci_buildTime", "04平均单测时间/min": "ci_testCaseTime_total", "05平均测试预测库时间/min": "ci_testFluidLibTime", \
        "06平均测试训练库时间/min": "ci_testFluidLibTrainTime", "07平均预测库大小/M": "ci_fluidInferenceSize", "08平均whl大小/M": "ci_WhlSize", \
        "09平均build目录大小/G": "ci_buildSize", "10单测总数/个": "ci_testCaseCount_total", "11单卡case总数/个": "ci_testCaseCount_single", \
        "12单卡case执行时间/min": "ci_testCaseTime_single", "13多卡case总数/个": "ci_testCaseCount_multi", "14多卡case执行时间/min": "ci_testCaseTime_multi", \
        "15独占case总数/个": "ci_testCaseCount_exclusive", "16独占case执行时间/min": "ci_testCaseTime_exclusive", "17平均失败率": "ci_failRate", \
        "18平均rerun率": "ci_rerunRate"}
    ci_index_key_list = sorted(ci_index_dic.keys())
    THISWEEK_CI_INDEX_First_LINE = "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
    for ci_name in CI_NAME_list:
        THISWEEK_CI_INDEX_First_LINE += "<td>{}</td>".format(ci_name)
    THISWEEK_CI_INDEX_First_LINE += "</tr>"
    THISWEEK_CI_INDEX_INFO = ""
    for i in range(len(ci_index_dic)):
        key = ci_index_key_list[i][2:]
        THISWEEK_CI_INDEX_INFO += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
            key)
        for ci_name in CI_NAME_list:
            if key == '平均单测时间/min' and ci_name in [
                    'PR-CI-Inference', 'PR-CI-CPU-Py2',
                    'PR-CI-Windows-OPENBLAS', 'FluidDoc1'
            ]:
                THISWEEK_CI_INDEX_INFO += "<td>None</td>"
            else:
                key = ci_index_dic[ci_index_key_list[i]].replace('ci', ci_name)
                if ciIndex_thisWeek[key] == None or ciIndex_thisWeek[
                        key] == "":
                    THISWEEK_CI_INDEX_INFO += "<td class='first'></td>"
                else:
                    THISWEEK_CI_INDEX_INFO += "<td>{}</td>".format(
                        ciIndex_thisWeek[key])
        THISWEEK_CI_INDEX_INFO += "</tr>"
    DETAIL_CI_INDEX_TABLE = THISWEEK_CI_INDEX_TITLE + THISWEEK_CI_INDEX_First_LINE + THISWEEK_CI_INDEX_INFO + "</table>"

    return KEY_CI_INDEX_TABLE, DETAIL_CI_INDEX_TABLE


def sendMail(ciIndex_thisWeek, ciIndex_lastWeek=0):
    COMMIT_AND_TIME = "<table border='1' align=center> <caption><font size='3'><b>用户感知指标</b></font></caption>"
    repo_list = localConfig.cf.get('ciIndex', 'commitCount').split(',')
    #用户感知指标: 各个repo的commit的数目
    for repo in repo_list:
        key = '%s_commitCount' % repo.split('/')[1]
        thisWeekCommit = ciIndex_thisWeek[key]
        lastWeekCommit = ciIndex_lastWeek[key] if ciIndex_lastWeek != 0 else 0
        if ciIndex_lastWeek == 0:
            DIFF_RATE = "%.2f" % float(
                (thisWeekCommit - 0.00001) / 0.00001 * 100)
        else:
            DIFF_RATE = "%.2f" % float(
                abs(thisWeekCommit - lastWeekCommit) / lastWeekCommit * 100)
        if thisWeekCommit - lastWeekCommit > 0:
            COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>%s commit数/个</td><td bgcolor='#ff6eb4'>%s(↑ %s" % (
                repo.split('/')[1], thisWeekCommit, DIFF_RATE)
            COMMIT_AND_TIME += "%)</td></tr>"
        else:
            COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>%s commit数/个</td><td bgcolor='#b5c4b1'>%s(↓ %s" % (
                repo.split('/')[1], thisWeekCommit, DIFF_RATE)
            COMMIT_AND_TIME += "%)</td></tr>"

    #用户感知指标: commit从提交到返回结果平均耗时
    thisweek_MAX_CONSUMTIME = 0
    CI_NAME_list = localConfig.cf.get('ciIndex', 'ci_name').split(',')  #所有的ci
    for ci in CI_NAME_list:
        if float(ciIndex_thisWeek['%s_average_consum_time' %
                                  ci]) > thisweek_MAX_CONSUMTIME:
            thisweek_MAX_CONSUMTIME = float(ciIndex_thisWeek[
                '%s_average_consum_time' % ci])
            max_CONSUMTIME_CI = ci
    lastweek_MAX_CONSUMTIME = float(ciIndex_lastWeek['%s_average_consum_time' %
                                                     max_CONSUMTIME_CI])
    consum_DIFF_RATE = "%.2f" % float(
        abs(thisweek_MAX_CONSUMTIME - lastweek_MAX_CONSUMTIME) /
        lastweek_MAX_CONSUMTIME * 100)
    if thisweek_MAX_CONSUMTIME - lastweek_MAX_CONSUMTIME > 0:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit从提交到返回结果平均耗时/min</td><td bgcolor='#ff6eb4'>%s(↑ %s" % (
            thisweek_MAX_CONSUMTIME, consum_DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"
    else:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit从提交到返回结果平均耗时/min</td><td bgcolor='#b5c4b1'>%s(↓ %s" % (
            thisweek_MAX_CONSUMTIME, consum_DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"

    #用户感知指标: commit从提交到返回结果最长耗时 
    thisweek_Longest_Time = float(ciIndex_thisWeek['LongestTime'])
    lastweek_Longest_Time = float(ciIndex_lastWeek['LongestTime'])
    longestTime_DIFF_RATE = "%.2f" % float(
        abs(thisweek_Longest_Time - lastweek_Longest_Time) /
        lastweek_Longest_Time * 100)
    if thisweek_Longest_Time - lastweek_Longest_Time > 0:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit从提交到返回结果最长耗时/min</td><td bgcolor='#ff6eb4'>%s(↑ %s" % (
            thisweek_Longest_Time, longestTime_DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"
    else:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>commit从提交到返回结果最长耗时/min</td><td bgcolor='#b5c4b1'>%s(↓ %s" % (
            thisweek_Longest_Time, longestTime_DIFF_RATE)
        COMMIT_AND_TIME += "%)</td></tr>"

    #用户感知指标: 单测随机挂引起的RERUN占比 
    thisWeek_rerun_index = testRerun(
        '%s 00:00:00' % ciIndex_thisWeek['startTime'],
        '%s 00:00:00' % ciIndex_thisWeek['endTime'])
    lastWeek_rerun_index = testRerun(
        '%s 00:00:00' % ciIndex_lastWeek['startTime'],
        '%s 00:00:00' % ciIndex_lastWeek['endTime'])
    rerun_DIFF_RATE = "%.2f" % float(
        abs(
            float(thisWeek_rerun_index['all_testfailed_rerunRatio']) - float(
                lastWeek_rerun_index['all_testfailed_rerunRatio'])))
    if float(thisWeek_rerun_index['all_testfailed_rerunRatio']) - float(
            lastWeek_rerun_index['all_testfailed_rerunRatio']) > 0:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的RERUN占比</td>"
        RERUN_INDEX_DIFF = "<td bgcolor='#ff6eb4'>%s" % thisWeek_rerun_index[
            'all_testfailed_rerunRatio'] + "%(↑ " + "%s" % rerun_DIFF_RATE + "%)</td>"
    else:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的RERUN占比</td>"
        RERUN_INDEX_DIFF = "<td bgcolor='#b5c4b1'>%s" % thisWeek_rerun_index[
            'all_testfailed_rerunRatio'] + "%(↓ " + "%s" % rerun_DIFF_RATE + "%)</td>"
    COMMIT_AND_TIME += RERUN_INDEX_DIFF
    COMMIT_AND_TIME += "</tr>"

    #用户感知指标: 平均失败率最大的CI及大小
    thisweek_MAX_FAILEDRATE = 0
    for ci in CI_NAME_list:
        if float(ciIndex_thisWeek['%s_failRate' %
                                  ci]) > thisweek_MAX_FAILEDRATE:
            thisweek_MAX_FAILEDRATE = float(ciIndex_thisWeek['%s_failRate' %
                                                             ci])
            max_FAILEDRATE_CI = ci
    lastweek_MAX_FAILEDRATE = float(ciIndex_lastWeek['%s_failRate' %
                                                     max_FAILEDRATE_CI])
    failed_DIFF_RATE = "%.2f" % float(
        abs(float(thisweek_MAX_FAILEDRATE) - float(lastweek_MAX_FAILEDRATE)) *
        100)
    if float(thisweek_MAX_FAILEDRATE) - float(lastweek_MAX_FAILEDRATE) > 0:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>平均失败率最大的CI及大小</td>"
        FAILED_INDEX_DIFF = "<td bgcolor='#ff6eb4'>%s: %.2f" % (
            max_FAILEDRATE_CI, thisweek_MAX_FAILEDRATE * 100
        ) + "%(↑ " + "%s" % failed_DIFF_RATE + "%)</td>"
    else:
        COMMIT_AND_TIME += "<tr align=center><td bgcolor='#d0d0d0'>平均失败率最大的CI及大小</td>"
        FAILED_INDEX_DIFF = "<td bgcolor='#b5c4b1'>%s: %.2f" % (
            max_FAILEDRATE_CI, thisweek_MAX_FAILEDRATE * 100
        ) + "%(↓ " + "%s" % failed_DIFF_RATE + "%)</td>"
    COMMIT_AND_TIME += FAILED_INDEX_DIFF
    COMMIT_AND_TIME += "</tr></table>"

    #效率云CI由于单测随机挂RERUN占比
    thisWeek_RERUN_TABLE = "<table border='1' align=center> <caption><font size='3'><b>效率云CI由于单测随机挂RERUN占比</b></font></caption>"
    thisWeek_RERUN_TABLE += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>整体</td><td>PR-CI-Coverage</td><td>	PR-CI-Py3</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td>"
    thisWeek_RERUN_TABLE += "</tr><tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的Rerun</td><td>%s" % thisWeek_rerun_index[
        'all_testfailed_rerunRatio']
    thisWeek_RERUN_TABLE += "%</td>"
    rerun_ci_by_utfail_list = localConfig.cf.get(
        'ciIndex', 'rerun_ci_by_utfail').split(',')
    for ci in rerun_ci_by_utfail_list:
        thisWeek_RERUN_TABLE += "<td>{}%</td>".format(thisWeek_rerun_index[
            '%s_testfailed_rerunRatio' % ci])
    thisWeek_RERUN_TABLE += "</tr></table>"

    #失败原因占比
    EXCODE_TABLE = excode('%s 00:00:00' % ciIndex_thisWeek['startTime'],
                          '%s 00:00:00' % ciIndex_thisWeek['endTime'])

    #对内关键指标与对内详细指标
    KEY_CI_INDEX_TABLE, DETAIL_CI_INDEX_TABLE = get_key_detail_ci_index(
        ciIndex_thisWeek, ciIndex_lastWeek)

    #汇总表格
    HTML_CONTENT = "<html><body><p>Hi, ALL:</p> <p>本周(%s 00:00:00 ~ %s 00:00:00)CI评价指标详细信息可参考如下表格:</p> <p>CI评价指标的计算方式可见: http://agroup.baidu.com/paddle-ci/md/article/3352500</p><p>现在机器资源如下: V100(coverage/py3) 17台, P4(Inference/CPU) 4台, Mac 8台, Windows 15台</p> %s" % (
        ciIndex_thisWeek['startTime'], ciIndex_thisWeek['endTime'],
        COMMIT_AND_TIME)
    HTML_CONTENT = HTML_CONTENT + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" \
        + KEY_CI_INDEX_TABLE + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" \
        + thisWeek_RERUN_TABLE + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" \
        + EXCODE_TABLE + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>"\
        + DETAIL_CI_INDEX_TABLE + "<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr><td height='10'></td</tr></table>" \
        + "<p>如有问题，请反馈到CE and CI值班群(xxx)或联系张春乐.</p> <p>张春乐</p></body></html>"

    mail = Mail()
    mail.set_sender('xxxx')
    mail.set_receivers(['xxxx@baidu.com'])
    mail.set_title('效率云%s~%s CI评价指标统计' % (ciIndex_thisWeek['startTime'],
                                          ciIndex_thisWeek['endTime']))
    mail.set_message(HTML_CONTENT, messageType='html', encoding='gb2312')
    mail.send()


def excode(startTime, endTime):
    """失败原因分析"""
    CI_NAME_list = localConfig.cf.get('ciIndex', 'ci_name').split(',')  #所有的ci
    startTime_stamp = strTimeTotimeStamp(startTime)
    endTime_stamp = strTimeTotimeStamp(endTime)
    EXCODE_TABLE = "<table border='1' align=center> <caption><font size='3'><b>效率云CI失败原因占比</b></font></caption>"
    EXCODE_TABLE += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
    failed_dic = {}
    for ci in CI_NAME_list:
        EXCODE_TABLE += "<td>{}</td>".format(ci)
        if ci == 'PR-CI-Mac':
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                ci, startTime_stamp, endTime_stamp)
        if ci == 'PR-CI-Windows':
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                ci, startTime_stamp, endTime_stamp)
        else:
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                ci, startTime_stamp, endTime_stamp)
        fail_commitCount = queryDB(fail_commitCount_query_stat, 'count')
        key = '%s_fail_commitCount' % ci
        failed_dic[key] = fail_commitCount
    excode_dic = {
        '示例代码失败': 5,
        '需要approve': 6,
        '编译失败': 7,
        '单测失败': 8,
        '覆盖率失败': 9
    }
    for i in ['示例代码失败', '编译失败', '单测失败', '覆盖率失败', '需要approve']:
        EXCODE_TABLE += "<tr align=center><td bgcolor='#d0d0d0'>%s</td>" % i
        for ci in CI_NAME_list:
            key = '%s_fail_commitCount' % ci
            fail_commitCount = failed_dic[key]
            excode = excode_dic[i]
            if ci == 'PR-CI-Mac':
                excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, excode, startTime_stamp, endTime_stamp)
            if ci == 'PR-CI-Windows':
                excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, excode, startTime_stamp, endTime_stamp)
            else:
                excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, excode, startTime_stamp, endTime_stamp)
            excode_commitCount = queryDB(excode_query_stat, 'count')
            excode_ratio = '%.2f' % (
                excode_commitCount / fail_commitCount * 100
            ) + '%' if excode_commitCount != None else None
            EXCODE_TABLE += "<td>{}</td>".format(excode_ratio)
        EXCODE_TABLE += "</tr>"
    EXCODE_TABLE += "</table>"
    return EXCODE_TABLE


def testRerun(startTime, endTime):
    startTime_stamp = strTimeTotimeStamp(startTime)
    endTime_stamp = strTimeTotimeStamp(endTime)
    rerun_index = {}
    for ci in [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Mac', 'PR-CI-Mac-Python3',
            'PR-CI-Windows'
    ]:
        rerunCount = {}
        count = 0
        ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and commit_createTime > %s and commit_createTime < %s and time > '2020-07-13 14:20:00'" % (
            ci, startTime_stamp, endTime_stamp)
        ALL_commitCount = queryDB(ALL_commitCount_query_stat, 'count')
        if ci == 'PR-CI-Mac':
            query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                ci, startTime_stamp, endTime_stamp)
        elif ci == 'PR-CI-Windows':
            query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                ci, startTime_stamp, endTime_stamp)
        else:
            query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s and time > '2020-07-13 14:20:00'" % (
                ci, startTime_stamp, endTime_stamp)
        db = Database()
        result = list(db.query(query_stat))
        for key in result[0]:
            commitId = key['commitId']
            if commitId not in rerunCount:
                rerunCount[commitId] = 1
            else:
                value = rerunCount[commitId]
                value += 1
                rerunCount[commitId] = value
        for commitId in rerunCount:
            if rerunCount[commitId] > 1:
                count += (rerunCount[commitId] - 1)
        rerun_index['%s_testfailed_rerunRatio' % ci] = '%.2f' % (
            count / ALL_commitCount * 100)
    rerun_index['all_testfailed_rerunRatio'] = '%.2f' % (
        float(rerun_index['PR-CI-Coverage_testfailed_rerunRatio']) +
        float(rerun_index['PR-CI-Py3_testfailed_rerunRatio']))
    return rerun_index


def regularCIMail_job():
    now = datetime.datetime.now()
    #获取今天零点
    zeroToday = now - datetime.timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond)
    #7天前0点
    before_7Days = zeroToday - datetime.timedelta(days=7)
    #14天前0点
    before_14Days = zeroToday - datetime.timedelta(days=14)
    ciIndex_thisWeek = queryCIDataWeekly(str(before_7Days), str(zeroToday))
    ciIndex_lastWeek = queryCIDataWeekly(str(before_14Days), str(before_7Days))
    sendMail(ciIndex_thisWeek, ciIndex_lastWeek)


regularCIMail_job()
