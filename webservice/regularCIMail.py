from utils.readConfig import ReadConfig
from utils.mail import Mail
from utils.db import Database
from utils.common import CommonModule
import datetime
import xlwt
import pandas as pd
import codecs

localConfig = ReadConfig()


class WeeklyCIIndex():
    def __init__(self):
        self.timeTypeCIindex = [
            'buildTime', 'testFluidLibTime', 'testFluidLibTrainTime',
            'testCaseTime_total', 'testCaseTime_single', 'testCaseTime_multi',
            'testCaseTime_exclusive'
        ]
        self.countTypeCIindex = [
            'fluidInferenceSize', 'WhlSize', 'buildSize',
            'testCaseCount_total', 'testCaseCount_single',
            'testCaseCount_multi', 'testCaseCount_exclusive', 'ccacheRate'
        ]
        self.requiredCIName = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Inference', 'PR-CI-CPU-Py2',
            'PR-CI-Mac', 'PR-CI-Mac-Python3', 'PR-CI-Windows',
            'PR-CI-Windows-OPENBLAS', 'FluidDoc1'
        ]
        self.notRequiredCIName = []
        self.ciNameHasTests = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Mac', 'PR-CI-Mac-Python3',
            'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS'
        ]
        self.repo = ['PaddlePaddle/Paddle', 'PaddlePaddle/FluidDoc']
        self.keyIndexDict = {
            "CI任务的平均耗时/min": "xly_average_consum_time_all_commit",
            "CI任务的平均排队时间/min": "xly_average_wait_time_all_commit",
            "CI任务的平均执行时间/min": "xly_average_exec_time_all_commit",
            "CI任务的平均耗时/min": "xly_average_consum_time_all_commit",
            "CI任务的平均排队时间/min": "xly_average_wait_time_all_commit",
            "CI任务的平均执行时间/min": "xly_average_exec_time_all_commit",
            "CI任务的平均编译时间/min": "xly_buildTime_all_commit",
            "平均ccache命中率/%": "xly_ccacheRate",
            "CI任务的平均单测时间/min": "xly_testCaseTime_total_all_commit",
            "平均rerun率/%": "xly_rerunRate",
            "平均失败率/%": "xly_failRate"
        }
        self.successIndexDict = {
            "成功CI任务的平均耗时/min": "xly_average_consum_time_success_commit",
            "成功CI任务的平均执行时间/min": "xly_average_exec_time_success_commit",
            "成功CI任务的平均排队时间/min": "xly_average_wait_time_success_commit",
            "成功CI任务的平均编译时间/min": "xly_buildTime_success_commit",
            "成功CI任务的平均单测时间/min": "xly_testCaseTime_total_success_commit"
        }
        self.exCodeDict = {
            '示例代码失败': 5,
            '需要approve': 6,
            '编译失败': 7,
            '单测失败': 8,
            '覆盖率失败': 9
        }
        self.common = CommonModule()
        self.db = Database()

    def getWeeklyCIIndex(self, startTime, endTime):
        """获取每周各个CI的详细指标"""
        ##db是7.9之后才开始有数据
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        ci_index = {}
        ci_index['startTime'] = startTime.split(' ')[0]
        ci_index['endTime'] = endTime.split(' ')[0]

        #不同repo的commit数目 
        for repo in self.repo:
            key = '%s_commitCount' % repo.split('/')[1]
            ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where repo='%s' and commit_createTime > %s and commit_createTime < %s" % (
                repo, startTime_stamp, endTime_stamp)
            ALL_commitCount = self.db.queryDB(ALL_commitCount_query_stat,
                                              'count')
            ci_index[key] = ALL_commitCount
        #时间指标: 所有commit执行时间/所有commit等待时间/耗时/成功commit执行时间/成功commit等待时间/成功commit的耗时
        for ci in self.requiredCIName:
            print(ci)
            if ci == 'PR-CI-Mac':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/' % ci
            elif ci == 'PR-CI-Windows':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/' % ci
            else:
                queryCIName = 'ciName =~ /^%s/' % ci

            #所有commit执行时间 (去除document_fix)
            average_exec_time_all_commit_query_stat = "select mean(execTime_total)/60 from paddle_ci_status where %s and documentfix='False' and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            average_exec_time_all_commit = self.db.queryDB(
                average_exec_time_all_commit_query_stat, 'mean')
            print(average_exec_time_all_commit_query_stat)
            key = '%s_average_exec_time_all_commit' % ci
            ci_index[
                key] = "%.2f" % average_exec_time_all_commit if average_exec_time_all_commit != None else None

            #所有commit等待时间
            average_wait_time_all_commit_query_stat = "select mean(waitTime_total)/60 from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            average_wait_time_all_commit = self.db.queryDB(
                average_wait_time_all_commit_query_stat, 'mean')
            key = '%s_average_wait_time_all_commit' % ci
            ci_index[
                key] = "%.2f" % average_wait_time_all_commit if average_wait_time_all_commit != None else None
            #所有commit耗时:执行+排队 
            key = '%s_average_consum_time_all_commit' % ci
            ci_index[key] = "%.2f" % (
                average_exec_time_all_commit + average_wait_time_all_commit
            ) if average_wait_time_all_commit != None or average_exec_time_all_commit != None else None
            #成功commit执行时间
            average_exec_time_success_commit_query_stat = "select mean(execTime_total)/60 from paddle_ci_status where %s and status='success' and EXCODE=0 and documentfix='False' and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            average_exec_time_success_commit = self.db.queryDB(
                average_exec_time_success_commit_query_stat, 'mean')
            key = '%s_average_exec_time_success_commit' % ci
            ci_index[
                key] = "%.2f" % average_exec_time_success_commit if average_exec_time_success_commit != None else None

            #成功commit等待时间
            average_wait_time_success_commit_query_stat = "select mean(waitTime_total)/60 from paddle_ci_status where %s and status='success' and EXCODE=0 and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            average_wait_time_success_commit = self.db.queryDB(
                average_wait_time_success_commit_query_stat, 'mean')
            key = '%s_average_wait_time_success_commit' % ci
            ci_index[
                key] = "%.2f" % average_wait_time_success_commit if average_wait_time_success_commit != None else None

            #成功commit耗时:执行+排队 
            key = '%s_average_consum_time_success_commit' % ci
            ci_index[key] = "%.2f" % (
                average_exec_time_success_commit +
                average_wait_time_success_commit
            ) if average_exec_time_success_commit != None or average_wait_time_success_commit != None else None

            #详细指标
            for index in self.timeTypeCIindex:
                if index in ['buildTime', 'testCaseTime_total']:
                    query_stat_success_commit = "select mean(%s)/60 from paddle_ci_index where %s and EXCODE=0 and createTime > %s and createTime < %s" % (
                        index, queryCIName, startTime_stamp, endTime_stamp)
                    average_value_success_commit = self.db.queryDB(
                        query_stat_success_commit, 'mean')
                    key = '%s_%s_success_commit' % (ci, index)
                    ci_index[
                        key] = "%.2f" % average_value_success_commit if average_value_success_commit != None else None

                query_stat = "select mean(%s)/60 from paddle_ci_index where %s and createTime > %s and createTime < %s" % (
                    index, queryCIName, startTime_stamp, endTime_stamp)
                average_value = self.db.queryDB(query_stat, 'mean')
                if index in ['buildTime', 'testCaseTime_total']:
                    key = '%s_%s_all_commit' % (ci, index)
                else:
                    key = '%s_%s' % (ci, index)
                ci_index[
                    key] = "%.2f" % average_value if average_value != None else None
            for index in self.countTypeCIindex:
                query_stat = "select mean(%s) from paddle_ci_index where %s and createTime > %s and createTime < %s" % (
                    index, queryCIName, startTime_stamp, endTime_stamp)
                average_value = self.db.queryDB(query_stat, 'mean')
                key = '%s_%s' % (ci, index)
                ci_index[
                    key] = "%.2f" % average_value if average_value != None else None
            #rerun率
            noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            noRepeat_commitCount = self.db.queryDB(
                noRepeat_commitCount_query_stat, 'count')
            all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            all_commitCount = self.db.queryDB(all_commitCount_query_stat,
                                              'count')
            key = "%s_rerunRate" % ci
            ci_index[key] = "%.2f" % (
                (1 - noRepeat_commitCount / all_commitCount) *
                100) if all_commitCount != None else 0
            #失败率
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and status='failure' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
                queryCIName, startTime_stamp, endTime_stamp)
            fail_commitCount = self.db.queryDB(fail_commitCount_query_stat,
                                               'count')
            key = "%s_failRate" % ci
            ci_index[key] = "%.2f" % ((fail_commitCount / all_commitCount) *
                                      100) if fail_commitCount != None else 0

        #所有commit最长耗时指标
        longest_time_all_commit_query_stat = 'SELECT MAX(t) from (SELECT waitTime_total+execTime_total as t from paddle_ci_status  where commit_createTime > %s and commit_createTime < %s)' % (
            startTime_stamp, endTime_stamp)
        longest_time_all_commit = self.db.queryDB(
            longest_time_all_commit_query_stat, 'max')
        ci_index['LongestTime_all_commit'] = '%.2f' % float(
            longest_time_all_commit / 60)
        longest_time_ci_query_stat = 'SELECT t,PR,ciName from (SELECT waitTime_total+execTime_total as t,PR,ciName from paddle_ci_status  where commit_createTime > %s and commit_createTime < %s) where t=%s' % (
            startTime_stamp, endTime_stamp, longest_time_all_commit)
        longest_time_ci = list(self.db.query(longest_time_ci_query_stat))
        ci_index['LongestTime_all_commit_PR'] = '%s' % longest_time_ci[0][0][
            'PR']
        ci_index['LongestTime_all_commit_CINAME'] = '%s' % longest_time_ci[0][
            0]['ciName']

        #成功commit最长耗时指标
        longest_time_success_commit_query_stat = "SELECT MAX(t) from (SELECT waitTime_total+execTime_total as t from paddle_ci_status  where status='success' and commit_createTime > %s and commit_createTime < %s)" % (
            startTime_stamp, endTime_stamp)
        longest_time_success_commit = self.db.queryDB(
            longest_time_success_commit_query_stat, 'max')
        ci_index['LongestTime_success_commit'] = '%.2f' % float(
            longest_time_success_commit / 60)
        longest_time_ci_query_stat = "SELECT t,PR,ciName from (SELECT waitTime_total+execTime_total as t,PR,ciName from paddle_ci_status  where status='success' and commit_createTime > %s and commit_createTime < %s) where t=%s" % (
            startTime_stamp, endTime_stamp, longest_time_success_commit)
        longest_time_ci = list(self.db.query(longest_time_ci_query_stat))

        ci_index['LongestTime_success_commit_PR'] = '%s' % longest_time_ci[0][
            0]['PR']
        ci_index['LongestTime_success_commit_CINAME'] = '%s' % longest_time_ci[
            0][0]['ciName']
        return ci_index

    def getRerunRatio(self, startTime, endTime):
        """获取由于单测随机挂引起的rerun率"""
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        rerun_index = {}
        all_testfailed_rerunRatio = 0.0
        for ci in self.ciNameHasTests:
            rerunCount = {}
            count = 0
            if ci == 'PR-CI-Mac':
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            elif ci == 'PR-CI-Windows':
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            else:
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            ALL_commitCount = self.db.queryDB(ALL_commitCount_query_stat,
                                              'count')

            if ci == 'PR-CI-Mac':
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            elif ci == 'PR-CI-Windows':
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            else:
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            result = list(self.db.query(query_stat))
            if len(result) == 0:
                rerun_index['%s_testfailed_rerunRatio' % ci] = 0
            else:
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
            all_testfailed_rerunRatio += float(rerun_index[
                '%s_testfailed_rerunRatio' % ci])
        rerun_index[
            'all_testfailed_rerunRatio'] = '%.2f' % all_testfailed_rerunRatio
        return rerun_index

    def getUserPerceptionIndexAndRerunByTestsFailed(self, ciIndex_thisWeek,
                                                    ciIndex_lastWeek):
        """
        表1: 用户感知指标: 
        1. commit数目
        2. 所有commit从提交到返回的平均耗时
        4. 所有commit从提交到返回的最长耗时CI及大小
        5. 单测随机挂引起的rerun率
        6. 平均失败率最大CI
        表2: 由于单测随机挂RERUN占比
        """
        rise_red_color = "<td bgcolor='#ff6eb4'>"
        decline_green_color = "<td bgcolor='#b5c4b1'>"
        UserPerceptionIndexContent = "<table border='1' align=center> <caption><font size='3'><b>用户感知指标</b></font></caption>"
        #各个repo的commit的数目
        for repo in self.repo:
            UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>%s CI任务/个</td>" % repo.split(
                '/')[1]
            key = '%s_commitCount' % repo.split('/')[1]
            thisWeekCommit = ciIndex_thisWeek[key]
            lastWeekCommit = ciIndex_lastWeek[key] if ciIndex_lastWeek[
                key] != None else 0
            if lastWeekCommit == 0 or ciIndex_lastWeek == 0:
                DIFF_RATE = "%.2f" % float(
                    (thisWeekCommit - 0.00001) / 0.00001 * 100)
            else:
                DIFF_RATE = "%.2f" % float(
                    abs(thisWeekCommit - lastWeekCommit) / lastWeekCommit *
                    100)
            if float(DIFF_RATE) > 50:  #比率大于50在显示颜色
                UserPerceptionIndexContent += "%s%s(↑ %s" % (
                    rise_red_color, thisWeekCommit, DIFF_RATE
                ) if thisWeekCommit - lastWeekCommit > 0 else "%s%s(↓ %s" % (
                    decline_green_color, thisWeekCommit, DIFF_RATE)
            else:
                UserPerceptionIndexContent += "<td>%s(↑ %s" % (
                    thisWeekCommit, DIFF_RATE
                ) if thisWeekCommit - lastWeekCommit > 0 else "<td>%s(↓ %s" % (
                    thisWeekCommit, DIFF_RATE)
            UserPerceptionIndexContent += "%)</td></tr>"

        #所有commit从提交到返回结果平均耗时/
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI任务从提交到返回结果平均耗时/min</td>"
        thisweek_max_consumtime_all_commit = 0
        thisweek_max_consumtime_success_commit = 0
        lastweek_max_consumtime_all_commit = 0
        lastweek_max_consumtime_success_commit = 0
        for ci in self.requiredCIName:
            key = '%s_average_consum_time_all_commit' % ci
            if float(ciIndex_thisWeek[
                    key]) > thisweek_max_consumtime_all_commit:
                thisweek_max_consumtime_all_commit = float(ciIndex_thisWeek[
                    key])
                thisweek_max_consumtime_ci = ci
            if float(ciIndex_lastWeek[
                    key]) > lastweek_max_consumtime_all_commit:
                lastweek_max_consumtime_all_commit = float(ciIndex_lastWeek[
                    key])
                lastweek_max_consumtime_ci = ci
        DIFF_RATE = "%.2f" % float(
            abs(thisweek_max_consumtime_all_commit -
                lastweek_max_consumtime_all_commit) /
            lastweek_max_consumtime_all_commit * 100)
        if float(DIFF_RATE) > 20:
            UserPerceptionIndexContent += "%s%s(↑ %s" % (
                rise_red_color, thisweek_max_consumtime_all_commit, DIFF_RATE
            ) if thisweek_max_consumtime_all_commit - lastweek_max_consumtime_all_commit > 0 else "%s%s(↓ %s" % (
                decline_green_color, thisweek_max_consumtime_all_commit,
                DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s(↑ %s" % (
                thisweek_max_consumtime_all_commit, DIFF_RATE
            ) if thisweek_max_consumtime_all_commit - lastweek_max_consumtime_all_commit > 0 else "<td>%s(↓ %s" % (
                thisweek_max_consumtime_all_commit, DIFF_RATE)
        UserPerceptionIndexContent += "%)</td></tr>"

        #所有commit从提交到返回的最长耗时CI及大小
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI任务从提交到返回结果最长耗时/min</td>"
        thisweek_longest_time_all_commit = float(ciIndex_thisWeek[
            'LongestTime_all_commit'])
        lastweek_longest_time_all_commit = float(ciIndex_lastWeek[
            'LongestTime_all_commit'])
        DIFF_RATE = "%.2f" % float(
            abs(thisweek_longest_time_all_commit -
                lastweek_longest_time_all_commit) /
            lastweek_longest_time_all_commit * 100)
        if float(DIFF_RATE) > 20:
            UserPerceptionIndexContent += "%s%s(↑ %s" % (
                rise_red_color, thisweek_longest_time_all_commit, DIFF_RATE
            ) if thisweek_longest_time_all_commit - lastweek_longest_time_all_commit > 0 else "%s%s(↓ %s" % (
                decline_green_color, thisweek_longest_time_all_commit,
                DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s(↑ %s" % (
                thisweek_longest_time_all_commit, DIFF_RATE
            ) if thisweek_longest_time_all_commit - lastweek_longest_time_all_commit > 0 else "<td>%s(↓ %s" % (
                thisweek_longest_time_all_commit, DIFF_RATE)
        UserPerceptionIndexContent += "%)"
        UserPerceptionIndexContent += "[%s %s]</td></tr>" % (
            ciIndex_thisWeek['LongestTime_all_commit_CINAME'],
            ciIndex_thisWeek['LongestTime_all_commit_PR'])

        #单测随机挂引起的RERUN占比 
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的RERUN占比</td>"
        thisWeek_rerun_index = self.getRerunRatio(
            '%s 00:00:00' % ciIndex_thisWeek['startTime'],
            '%s 00:00:00' % ciIndex_thisWeek['endTime'])
        lastWeek_rerun_index = self.getRerunRatio(
            '%s 00:00:00' % ciIndex_lastWeek['startTime'],
            '%s 00:00:00' % ciIndex_lastWeek['endTime'])
        DIFF_RATE = "%.2f" % float(
            abs(
                float(thisWeek_rerun_index['all_testfailed_rerunRatio']) -
                float(lastWeek_rerun_index['all_testfailed_rerunRatio'])))
        if float(DIFF_RATE) > 3 or float(thisWeek_rerun_index[
                'all_testfailed_rerunRatio']) > 5:  #变化率大于3%或本周的单测随机挂大于5%
            UserPerceptionIndexContent += "%s%s(↑ %s" % (
                rise_red_color,
                float(thisWeek_rerun_index['all_testfailed_rerunRatio']),
                DIFF_RATE) if float(thisWeek_rerun_index[
                    'all_testfailed_rerunRatio']) - float(lastWeek_rerun_index[
                        'all_testfailed_rerunRatio']) > 0 else "%s%s(↓ %s" % (
                            decline_green_color, float(thisWeek_rerun_index[
                                'all_testfailed_rerunRatio']), DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s(↑ %s" % (
                float(thisWeek_rerun_index['all_testfailed_rerunRatio']),
                DIFF_RATE
            ) if float(thisWeek_rerun_index[
                'all_testfailed_rerunRatio']) - float(lastWeek_rerun_index[
                    'all_testfailed_rerunRatio']) > 0 else "<td>%s(↓ %s" % (
                        float(thisWeek_rerun_index[
                            'all_testfailed_rerunRatio']), DIFF_RATE)
        UserPerceptionIndexContent += "%)</td></tr>"

        #平均失败率最大的CI及大小
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>平均失败率最大的CI及大小</td>"
        thisweek_max_failrate = 0
        lastweek_max_failrate = 0
        for ci in self.requiredCIName:
            if ci not in ['FluidDoc1']:
                key = '%s_failRate' % ci
                if float(ciIndex_thisWeek[key]) > thisweek_max_failrate:
                    thisweek_max_failrate = float(ciIndex_thisWeek[key])
                    thisweek_max_failrate_ci = ci
                if float(ciIndex_lastWeek[key]) > lastweek_max_failrate:
                    lastweek_max_failrate = float(ciIndex_lastWeek[key])
                    lastweek_max_failrate_ci = ci
        DIFF_RATE = "%.2f" % float(
            abs(float(thisweek_max_failrate) - float(lastweek_max_failrate)))
        if float(DIFF_RATE) > 5:  #失败率变化大于5%
            UserPerceptionIndexContent += "%s%s(↑ %s" % (
                rise_red_color, thisweek_max_failrate, DIFF_RATE
            ) if thisweek_max_failrate - lastweek_max_failrate > 0 else "%s%s(↓ %s" % (
                decline_green_color, thisweek_max_failrate, DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s(↑ %s" % (
                thisweek_max_failrate, DIFF_RATE
            ) if thisweek_max_failrate - lastweek_max_failrate > 0 else "<td>%s(↓ %s" % (
                thisweek_max_failrate, DIFF_RATE)
        UserPerceptionIndexContent += "%)"
        UserPerceptionIndexContent += "[%s]</td></tr></table>" % thisweek_max_failrate_ci

        #由于单测随机挂RERUN占比
        rerunRatioByTestsFailedContent = "<table border='1' align=center> <caption><font size='3'><b>效率云CI由于单测随机挂RERUN占比</b></font></caption>"
        rerunRatioByTestsFailedContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>整体</td>"
        for ci in self.ciNameHasTests:
            rerunRatioByTestsFailedContent += "<td>%s</td>" % ci
        rerunRatioByTestsFailedContent += "</tr><tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的Rerun</td><td>%s" % thisWeek_rerun_index[
            'all_testfailed_rerunRatio']
        rerunRatioByTestsFailedContent += "%</td>"

        for ci in self.ciNameHasTests:
            rerunRatioByTestsFailedContent += "<td>{}%</td>".format(
                thisWeek_rerun_index['%s_testfailed_rerunRatio' % ci])
        rerunRatioByTestsFailedContent += "</tr></table>"
        return UserPerceptionIndexContent, rerunRatioByTestsFailedContent

    def getInternalKeyIndex(self, ciIndex_thisWeek, ciIndex_lastWeek=0):
        """获取效率云对内关键指标"""
        InternalKeyIndexContent = "<table border='1' align=center> <caption><font size='3'><b>效率云对内关键指标</b></font></caption>"
        startTime = ciIndex_thisWeek['startTime']
        endTime = ciIndex_thisWeek['endTime']
        InternalKeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            InternalKeyIndexContent += "<td>%s</td>" % ci
        InternalKeyIndexContent += "</tr>"
        for index in self.keyIndexDict:
            InternalKeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>%s(本周值|上周值|浮动)</td>" % index
            for ci in self.requiredCIName:
                if index == '平均编译时间/min' and ci in ['FluidDoc1']:
                    InternalKeyIndexContent += "<td>None</td>"
                elif index == '平均单测时间/min' and ci in [
                        'PR-CI-Inference', 'PR-CI-CPU-Py2', 'FluidDoc1'
                ]:
                    InternalKeyIndexContent += "<td>None</td>"
                elif index == '平均ccache命中率/%' and ci in [
                        'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS'
                ]:
                    InternalKeyIndexContent += "<td>None</td>"
                else:
                    key = self.keyIndexDict[index].replace('xly', ci)
                    if index in ['平均rerun率/%', '平均失败率/%', 'ccache平均命中率/%']:
                        # 这俩参数已经是百分率了
                        thisWeek_lastWeek_radio = float(ciIndex_thisWeek[
                            key]) - float(ciIndex_lastWeek[key])
                    else:
                        if ciIndex_thisWeek[key] == None:  #本周无值
                            value = 'None | %s' % (ciIndex_lastWeek[key])
                            InternalKeyIndexContent += "<td>%s</td>" % value
                            continue
                        elif ciIndex_lastWeek[key] == None:  #上周偶无值
                            value = '%s | None' % (ciIndex_thisWeek[key])
                            InternalKeyIndexContent += "<td>%s</td>" % value
                            continue
                        else:
                            thisWeek_lastWeek_radio = float(
                                (float(ciIndex_thisWeek[key]) -
                                 float(ciIndex_lastWeek[key])) /
                                float(ciIndex_lastWeek[key])
                            ) if ciIndex_lastWeek[key] != 0 else float(
                                (float(ciIndex_thisWeek[key]) - 0.00001
                                 )) / 0.00001
                    value = '%s | %s' % (ciIndex_thisWeek[key],
                                         ciIndex_lastWeek[key])

                    if thisWeek_lastWeek_radio >= 0:
                        if index in ['平均rerun率/%', '平均失败率/%', 'ccache平均命中率/%']:
                            value = value + ' |↑%.2f' % (
                                thisWeek_lastWeek_radio) + '%'
                            standard_radio = 5  #本身已经是百分率了
                        else:
                            value = value + ' |↑%.2f' % (
                                thisWeek_lastWeek_radio * 100) + '%'
                            standard_radio = 0.05
                        if thisWeek_lastWeek_radio >= standard_radio:
                            InternalKeyIndexContent += "<td bgcolor='#ff6eb4'>{}</td>".format(
                                value)
                        else:
                            InternalKeyIndexContent += "<td>{}</td>".format(
                                value)
                    elif thisWeek_lastWeek_radio < 0:
                        if index in ['平均rerun率/%', '平均失败率/%']:
                            value = value + ' |↓%.2f' % (
                                abs(thisWeek_lastWeek_radio)) + '%'
                            standard_radio = 5
                        else:
                            value = value + ' |↓%.2f' % (
                                abs(thisWeek_lastWeek_radio) * 100) + '%'
                            standard_radio = 0.05
                        if thisWeek_lastWeek_radio <= -standard_radio:
                            InternalKeyIndexContent += "<td bgcolor='#b5c4b1'>{}</td>".format(
                                value)
                        else:
                            InternalKeyIndexContent += "<td>{}</td>".format(
                                value)
        InternalKeyIndexContent += "</tr></table>"
        return InternalKeyIndexContent

    def getInternalDetailIndex(self, ciIndex_thisWeek, ciIndex_lastWeek=0):
        """获取内部本周详细指标"""
        InternalDetailIndexContent = "<table border='1' align=center> <caption><font size='3'><b>效率云对内详细指标</b></font></caption>"
        ci_index_dic = {"04CI任务的平均耗时/min": "ci_average_consum_time_all_commit", \
            "05CI任务的平均排队时间/min": "ci_average_wait_time_all_commit", "06CI任务的平均执行时间/min": "ci_average_exec_time_all_commit", \
            "07平均编译时间/min": "ci_buildTime_all_commit", "08平均ccache命中率/%": "ci_ccacheRate", \
            "09平均单测时间/min": "ci_testCaseTime_total_all_commit", "10平均测试预测库时间/min": "ci_testFluidLibTime", \
            "11平均测试训练库时间/min": "ci_testFluidLibTrainTime", "12平均预测库大小/M": "ci_fluidInferenceSize", "13平均whl大小/M": "ci_WhlSize", \
            "14平均build目录大小/G": "ci_buildSize", "15单测总数/个": "ci_testCaseCount_total", "16单卡case总数/个": "ci_testCaseCount_single", \
            "17单卡case执行时间/min": "ci_testCaseTime_single", "18多卡case总数/个": "ci_testCaseCount_multi", "19多卡case执行时间/min": "ci_testCaseTime_multi", \
            "20独占case总数/个": "ci_testCaseCount_exclusive", "21独占case执行时间/min": "ci_testCaseTime_exclusive", "22平均失败率": "ci_failRate", \
            "23平均rerun率": "ci_rerunRate"}
        #"00成功任务的平均耗时/min": "ci_average_consum_time_success_commit", 
        #"01成功任务的平均排队时间/min": "ci_average_wait_time_success_commit", 
        #"02成功任务的平均执行时间/min": "ci_average_exec_time_success_commit",
        # "03成功任务的平均编译时间/min": "ci_buildTime_success_commit"
        # "04成功任务的平均单测时间/min": "ci_testCaseTime_total_success_commit"
        ci_index_key_list = sorted(ci_index_dic.keys())
        InternalDetailIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            InternalDetailIndexContent += "<td>{}</td>".format(ci)
        InternalDetailIndexContent += "</tr>"

        THISWEEK_CI_INDEX_INFO = ""
        for i in range(len(ci_index_dic)):
            key = ci_index_key_list[i][2:]
            InternalDetailIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
                key)
            for ci_name in self.requiredCIName:
                if key == '平均单测时间/min' and ci_name in [
                        'PR-CI-Inference', 'PR-CI-CPU-Py2', 'FluidDoc1'
                ]:
                    InternalDetailIndexContent += "<td>None</td>"
                elif key == '平均ccache命中率/%' and ci_name in [
                        'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS'
                ]:
                    InternalDetailIndexContent += "<td>None</td>"
                else:
                    key = ci_index_dic[ci_index_key_list[i]].replace('ci',
                                                                     ci_name)
                    if ciIndex_thisWeek[key] == None or ciIndex_thisWeek[
                            key] == "":
                        InternalDetailIndexContent += "<td class='first'></td>"
                    else:
                        InternalDetailIndexContent += "<td>{}</td>".format(
                            ciIndex_thisWeek[key])
            InternalDetailIndexContent += "</tr>"
        return InternalDetailIndexContent

    def getExcodeIndex(self, startTime, endTime):
        """失败原因分析"""
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        exCodeContent = "<table border='1' align=center> <caption><font size='3'><b>效率云CI失败原因占比</b></font></caption>"
        exCodeContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        failed_dic = {}
        for ci in self.requiredCIName:
            exCodeContent += "<td>{}</td>".format(ci)
            if ci == 'PR-CI-Mac':
                fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            if ci == 'PR-CI-Windows':
                fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            else:
                fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            fail_commitCount = self.db.queryDB(fail_commitCount_query_stat,
                                               'count')
            key = '%s_fail_commitCount' % ci
            failed_dic[key] = fail_commitCount

        for i in self.exCodeDict:
            exCodeContent += "<tr align=center><td bgcolor='#d0d0d0'>%s</td>" % i
            for ci in self.requiredCIName:
                key = '%s_fail_commitCount' % ci
                fail_commitCount = failed_dic[key]
                excode = self.exCodeDict[i]
                if ci == 'PR-CI-Mac':
                    excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                        ci, excode, startTime_stamp, endTime_stamp)
                if ci == 'PR-CI-Windows':
                    excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                        ci, excode, startTime_stamp, endTime_stamp)
                else:
                    excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                        ci, excode, startTime_stamp, endTime_stamp)
                excode_commitCount = self.db.queryDB(excode_query_stat,
                                                     'count')
                excode_ratio = '%.2f' % (
                    excode_commitCount / fail_commitCount * 100
                ) + '%' if excode_commitCount != None else None
                exCodeContent += "<td>{}</td>".format(excode_ratio)
            exCodeContent += "</tr>"
        exCodeContent += "</table>"
        return exCodeContent

    def getSuccessIndex(self, ciIndex_thisWeek, ciIndex_lastWeek=0):
        """成功任务的CI指标"""
        SuccessKeyIndexContent = "<table border='1' align=center> <caption><font size='3'><b>效率云成功CI任务的关键指标</b></font></caption>"
        startTime = ciIndex_thisWeek['startTime']
        endTime = ciIndex_thisWeek['endTime']
        SuccessKeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            SuccessKeyIndexContent += "<td>%s</td>" % ci
        SuccessKeyIndexContent += "</tr>"
        for index in self.successIndexDict:
            SuccessKeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>%s(本周值|上周值|浮动)</td>" % index
            for ci in self.requiredCIName:
                key = self.successIndexDict[index].replace('xly', ci)
                if ciIndex_thisWeek[key] == None:  #本周无值
                    value = 'None | %s' % (ciIndex_lastWeek[key])
                    SuccessKeyIndexContent += "<td>%s</td>" % value
                    continue
                elif ciIndex_lastWeek[key] == None:  #上周偶无值
                    value = '%s | None' % (ciIndex_thisWeek[key])
                    SuccessKeyIndexContent += "<td>%s</td>" % value
                    continue
                else:
                    thisWeek_lastWeek_radio = float((
                        float(ciIndex_thisWeek[key]) -
                        float(ciIndex_lastWeek[key])) / float(ciIndex_lastWeek[
                            key])) if ciIndex_lastWeek[key] != 0 else float(
                                (float(ciIndex_thisWeek[key]) - 0.00001
                                 )) / 0.00001
                value = '%s | %s' % (ciIndex_thisWeek[key],
                                     ciIndex_lastWeek[key])
                if thisWeek_lastWeek_radio >= 0:
                    value = value + ' |↑%.2f' % (thisWeek_lastWeek_radio * 100
                                                 ) + '%'
                    standard_radio = 0.05
                    if thisWeek_lastWeek_radio >= standard_radio:
                        SuccessKeyIndexContent += "<td bgcolor='#ff6eb4'>{}</td>".format(
                            value)
                    else:
                        SuccessKeyIndexContent += "<td>{}</td>".format(value)
                else:
                    value = value + ' |↓%.2f' % (abs(thisWeek_lastWeek_radio) *
                                                 100) + '%'
                    standard_radio = 0.05
                    if thisWeek_lastWeek_radio <= -standard_radio:
                        SuccessKeyIndexContent += "<td bgcolor='#b5c4b1'>{}</td>".format(
                            value)
                    else:
                        SuccessKeyIndexContent += "<td>{}</td>".format(value)
        SuccessKeyIndexContent += "</tr></table>"
        return SuccessKeyIndexContent


def sendMail(startTime, endTime, Content):
    mail = Mail()
    mail.set_sender('xxx@baidu.com')
    mail.set_receivers(['xxx-all@baidu.com'])
    mail.set_title('效率云%s~%s CI评价指标统计' % (startTime, endTime))
    mail.set_message(Content, messageType='html', encoding='gb2312')
    mail.send()


def main():
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
    WeeklyCI = WeeklyCIIndex()
    ciIndex_thisWeek = WeeklyCI.getWeeklyCIIndex(
        str(before_7Days), str(zeroToday))
    ciIndex_lastWeek = WeeklyCI.getWeeklyCIIndex(
        str(before_14Days), str(before_7Days))

    UserPerceptionIndexContent, rerunRatioByTestsFailedContent = WeeklyCI.getUserPerceptionIndexAndRerunByTestsFailed(
        ciIndex_thisWeek, ciIndex_lastWeek)

    InternalKeyIndexContent = WeeklyCI.getInternalKeyIndex(ciIndex_thisWeek,
                                                           ciIndex_lastWeek)
    exCodeContent = WeeklyCI.getExcodeIndex(
        '%s 00:00:00' % ciIndex_thisWeek['startTime'],
        '%s 00:00:00' % ciIndex_thisWeek['endTime'])
    successKeyIndexContent = WeeklyCI.getSuccessIndex(ciIndex_thisWeek,
                                                      ciIndex_lastWeek)
    InternalDetailIndexContent = WeeklyCI.getInternalDetailIndex(
        ciIndex_thisWeek, ciIndex_lastWeek)

    MailContent = "<html><body><p>Hi, ALL:</p> <p>本周(%s 00:00:00 ~ %s 00:00:00)CI评价指标详细信息可参考如下表格:</p> <p>CI评价指标的计算方式可见: http://agroup.baidu.com/paddle-ci/md/article/3352500</p><p>现在机器资源如下: V100(coverage/py3) 17台, P4(Inference/CPU) 4台, Mac 7台, Windows 23台</p>" % (
        ciIndex_thisWeek['startTime'], ciIndex_thisWeek['endTime'])
    MailContent += UserPerceptionIndexContent

    MailContent += InternalKeyIndexContent
    MailContent += rerunRatioByTestsFailedContent
    MailContent += exCodeContent
    MailContent += successKeyIndexContent
    MailContent += InternalDetailIndexContent

    MailContent = "<html><body><p>Hi, ALL:</p> <p>本周(2020-12-28 00:00:00 ~ 2021-01-04 00:00:00)CI评价指标详细信息可参考如下表格:</p> <p>CI评价指标的计算方式可见: http://agroup.baidu.com/paddle-ci/md/article/3352500</p><p>现在机器资源如下: V100(coverage/py3) 17台, P4(Inference/CPU) 4台, Mac 7台, Windows 23台</p><table border='1' align=center> <caption><font size='3'><b>用户感知指标</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>Paddle CI任务/个</td><td>3494(↑ 16.00%)</td></tr><tr align=center><td bgcolor='#d0d0d0'>FluidDoc CI任务/个</td><td bgcolor='#ff6eb4'>33(↑ 175.00%)</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务从提交到返回结果平均耗时/min</td><td bgcolor='#ff6eb4'>130.57(↑ 27.41%)</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务从提交到返回结果最长耗时/min</td><td bgcolor='#ff6eb4'>402.57(↑ 52.92%)[PR-CI-Windows 29989]</td></tr><tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的RERUN占比</td><td bgcolor='#ff6eb4'>6.36(↑ 1.13%)</td></tr><tr align=center><td bgcolor='#d0d0d0'>平均失败率最大的CI及大小</td><td>44.81(↑ 1.87%)[PR-CI-Coverage]</td></tr></table><table border='1' align=center> <caption><font size='3'><b>效率云对内关键指标</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>PR-CI-Coverage</td><td>PR-CI-Py3</td><td>PR-CI-Inference</td><td>PR-CI-CPU-Py2</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td><td>PR-CI-Windows-OPENBLAS</td><td>FluidDoc1</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均耗时/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>79.30 | 99.50 |↓20.30%</td><td>60.79 | 62.90 |↓3.35%</td><td bgcolor='#b5c4b1'>45.85 | 58.97 |↓22.25%</td><td bgcolor='#b5c4b1'>46.33 | 56.83 |↓18.48%</td><td bgcolor='#b5c4b1'>21.98 | 29.56 |↓25.64%</td><td bgcolor='#b5c4b1'>32.18 | 34.85 |↓7.66%</td><td bgcolor='#ff6eb4'>130.57 | 102.48 |↑27.41%</td><td>36.65 | 37.32 |↓1.80%</td><td bgcolor='#b5c4b1'>58.95 | 73.91 |↓20.24%</td><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均排队时间/min(本周值|上周值|浮动)</td><td bgcolor='#ff6eb4'>10.97 | 8.48 |↑29.36%</td><td bgcolor='#ff6eb4'>10.14 | 6.07 |↑67.05%</td><td bgcolor='#b5c4b1'>31.59 | 39.52 |↓20.07%</td><td bgcolor='#b5c4b1'>32.92 | 40.91 |↓19.53%</td><td bgcolor='#b5c4b1'>3.86 | 4.56 |↓15.35%</td><td bgcolor='#ff6eb4'>5.01 | 3.30 |↑51.82%</td><td bgcolor='#ff6eb4'>45.22 | 5.81 |↑678.31%</td><td bgcolor='#ff6eb4'>1.74 | 0.91 |↑91.21%</td><td bgcolor='#b5c4b1'>51.65 | 68.71 |↓24.83%</td><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均执行时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>68.33 | 91.02 |↓24.93%</td><td bgcolor='#b5c4b1'>50.64 | 56.83 |↓10.89%</td><td bgcolor='#b5c4b1'>14.25 | 19.44 |↓26.70%</td><td bgcolor='#b5c4b1'>13.41 | 15.92 |↓15.77%</td><td bgcolor='#b5c4b1'>18.12 | 25.00 |↓27.52%</td><td bgcolor='#b5c4b1'>27.17 | 31.55 |↓13.88%</td><td bgcolor='#b5c4b1'>85.36 | 96.67 |↓11.70%</td><td>34.91 | 36.40 |↓4.09%</td><td bgcolor='#ff6eb4'>7.30 | 5.20 |↑40.38%</td><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均编译时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>21.28 | 36.60 |↓41.86%</td><td bgcolor='#b5c4b1'>13.90 | 22.10 |↓37.10%</td><td bgcolor='#b5c4b1'>7.40 | 13.74 |↓46.14%</td><td bgcolor='#b5c4b1'>3.30 | 5.55 |↓40.54%</td><td bgcolor='#b5c4b1'>5.76 | 8.52 |↓32.39%</td><td bgcolor='#b5c4b1'>6.08 | 9.18 |↓33.77%</td><td bgcolor='#b5c4b1'>35.68 | 47.70 |↓25.20%</td><td>22.87 | 23.63 |↓3.22%</td><td>None | None</td><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均单测时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>50.01 | 53.43 |↓6.40%</td><td bgcolor='#ff6eb4'>38.13 | 34.51 |↑10.49%</td><td>None | None</td><td>None | None</td><td bgcolor='#b5c4b1'>13.56 | 16.21 |↓16.35%</td><td>20.04 | 20.18 |↓0.69%</td><td>54.81 | 56.21 |↓2.49%</td><td>12.81 | 13.47 |↓4.90%</td><td>None | None</td><tr align=center><td bgcolor='#d0d0d0'>平均rerun率/%(本周值|上周值|浮动)</td><td bgcolor='#ff6eb4'>18.40 | 10.17 |↑8.23%</td><td>6.99 | 6.06 |↑0.93%</td><td>1.28 | 0.51 |↑0.77%</td><td>6.88 | 5.74 |↑1.14%</td><td>3.02 | 0.46 |↑2.56%</td><td>1.19 | 2.31 |↓1.12%</td><td bgcolor='#ff6eb4'>35.08 | 21.03 |↑14.05%</td><td>5.98 | 9.91 |↓3.93%</td><td bgcolor='#ff6eb4'>24.24 | 8.33 |↑15.91%</td><tr align=center><td bgcolor='#d0d0d0'>平均失败率/%(本周值|上周值|浮动)</td><td>44.81 | 42.94 |↑1.87%</td><td>31.88 | 30.81 |↑1.07%</td><td>7.69 | 5.05 |↑2.64%</td><td>36.03 | 33.97 |↑2.06%</td><td bgcolor='#ff6eb4'>26.79 | 19.44 |↑7.35%</td><td>25.00 | 21.30 |↑3.70%</td><td bgcolor='#b5c4b1'>22.62 | 30.47 |↓7.85%</td><td bgcolor='#ff6eb4'>30.28 | 22.84 |↑7.44%</td><td bgcolor='#ff6eb4'>66.67 | 50.00 |↑16.67%</td></tr></table><table border='1' align=center> <caption><font size='3'><b>效率云CI由于单测随机挂RERUN占比</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>整体</td><td>PR-CI-Coverage</td><td>PR-CI-Py3</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td><td>PR-CI-Windows-OPENBLAS</td></tr><tr align=center><td bgcolor='#d0d0d0'>单测随机挂引起的Rerun</td><td>6.36%</td><td>1.42%</td><td>0.44%</td><td>0.75%</td><td>0.00%</td><td>2.95%</td><td>0.80%</td></tr></table><table border='1' align=center> <caption><font size='3'><b>效率云CI失败原因占比</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>PR-CI-Coverage</td><td>PR-CI-Py3</td><td>PR-CI-Inference</td><td>PR-CI-CPU-Py2</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td><td>PR-CI-Windows-OPENBLAS</td><td>FluidDoc1</td><tr align=center><td bgcolor='#d0d0d0'>示例代码失败</td><td>None</td><td>None</td><td>None</td><td>5.62%</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td></tr><tr align=center><td bgcolor='#d0d0d0'>需要approve</td><td>None</td><td>None</td><td>None</td><td>42.70%</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td></tr><tr align=center><td bgcolor='#d0d0d0'>编译失败</td><td>41.05%</td><td>46.58%</td><td>100.00%</td><td>24.72%</td><td>52.24%</td><td>57.14%</td><td>46.38%</td><td>52.63%</td><td>None</td></tr><tr align=center><td bgcolor='#d0d0d0'>单测失败</td><td>30.53%</td><td>47.95%</td><td>None</td><td>None</td><td>39.55%</td><td>39.68%</td><td>50.72%</td><td>44.74%</td><td>None</td></tr><tr align=center><td bgcolor='#d0d0d0'>覆盖率失败</td><td>15.79%</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td><td>None</td></tr></table><table border='1' align=center> <caption><font size='3'><b>效率云成功CI任务的关键指标</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>PR-CI-Coverage</td><td>PR-CI-Py3</td><td>PR-CI-Inference</td><td>PR-CI-CPU-Py2</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td><td>PR-CI-Windows-OPENBLAS</td><td>FluidDoc1</td></tr><tr align=center><td bgcolor='#d0d0d0'>成功CI任务的平均耗时/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>94.72 | 107.29 |↓11.72%</td><td>69.51 | 71.31 |↓2.52%</td><td bgcolor='#b5c4b1'>47.32 | 59.67 |↓20.70%</td><td bgcolor='#b5c4b1'>48.87 | 61.56 |↓20.61%</td><td bgcolor='#b5c4b1'>25.06 | 31.10 |↓19.42%</td><td>37.11 | 36.76 |↑0.95%</td><td bgcolor='#ff6eb4'>130.52 | 110.45 |↑18.17%</td><td>38.56 | 38.31 |↑0.65%</td><td bgcolor='#b5c4b1'>54.35 | 72.54 |↓25.08%</td><tr align=center><td bgcolor='#d0d0d0'>成功CI任务的平均执行时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>81.53 | 97.57 |↓16.44%</td><td bgcolor='#b5c4b1'>57.99 | 65.33 |↓11.24%</td><td bgcolor='#b5c4b1'>15.07 | 20.21 |↓25.43%</td><td bgcolor='#b5c4b1'>14.04 | 17.20 |↓18.37%</td><td bgcolor='#b5c4b1'>20.74 | 26.13 |↓20.63%</td><td bgcolor='#b5c4b1'>31.60 | 33.34 |↓5.22%</td><td bgcolor='#b5c4b1'>89.87 | 104.43 |↓13.94%</td><td>36.82 | 37.63 |↓2.15%</td><td bgcolor='#ff6eb4'>5.81 | 2.40 |↑142.08%</td><tr align=center><td bgcolor='#d0d0d0'>成功CI任务的平均排队时间/min(本周值|上周值|浮动)</td><td bgcolor='#ff6eb4'>13.19 | 9.73 |↑35.56%</td><td bgcolor='#ff6eb4'>11.51 | 5.97 |↑92.80%</td><td bgcolor='#b5c4b1'>32.25 | 39.46 |↓18.27%</td><td bgcolor='#b5c4b1'>34.83 | 44.35 |↓21.47%</td><td bgcolor='#b5c4b1'>4.32 | 4.97 |↓13.08%</td><td bgcolor='#ff6eb4'>5.51 | 3.42 |↑61.11%</td><td bgcolor='#ff6eb4'>40.65 | 6.02 |↑575.25%</td><td bgcolor='#ff6eb4'>1.74 | 0.68 |↑155.88%</td><td bgcolor='#b5c4b1'>48.55 | 70.14 |↓30.78%</td><tr align=center><td bgcolor='#d0d0d0'>成功CI任务的平均编译时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>21.59 | 32.75 |↓34.08%</td><td bgcolor='#b5c4b1'>14.43 | 22.04 |↓34.53%</td><td bgcolor='#b5c4b1'>7.40 | 13.74 |↓46.14%</td><td bgcolor='#b5c4b1'>3.08 | 5.45 |↓43.49%</td><td bgcolor='#b5c4b1'>5.67 | 8.41 |↓32.58%</td><td bgcolor='#b5c4b1'>6.12 | 8.96 |↓31.70%</td><td bgcolor='#b5c4b1'>35.50 | 48.28 |↓26.47%</td><td>22.82 | 23.27 |↓1.93%</td><td>None | None</td><tr align=center><td bgcolor='#d0d0d0'>成功CI任务的平均单测时间/min(本周值|上周值|浮动)</td><td bgcolor='#b5c4b1'>49.52 | 56.82 |↓12.85%</td><td>38.30 | 39.18 |↓2.25%</td><td>None | None</td><td>None | None</td><td bgcolor='#b5c4b1'>13.58 | 16.08 |↓15.55%</td><td>20.18 | 20.52 |↓1.66%</td><td>53.89 | 55.12 |↓2.23%</td><td bgcolor='#b5c4b1'>12.07 | 12.79 |↓5.63%</td><td>None | None</td></tr></table><table border='1' align=center> <caption><font size='3'><b>效率云对内详细指标</b></font></caption><tr align=center><td bgcolor='#d0d0d0'>CI名称</td><td>PR-CI-Coverage</td><td>PR-CI-Py3</td><td>PR-CI-Inference</td><td>PR-CI-CPU-Py2</td><td>PR-CI-Mac</td><td>PR-CI-Mac-Python3</td><td>PR-CI-Windows</td><td>PR-CI-Windows-OPENBLAS</td><td>FluidDoc1</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均耗时/min</td><td>79.30</td><td>60.79</td><td>45.85</td><td>46.33</td><td>21.98</td><td>32.18</td><td>130.57</td><td>36.65</td><td>58.95</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均排队时间/min</td><td>10.97</td><td>10.14</td><td>31.59</td><td>32.92</td><td>3.86</td><td>5.01</td><td>45.22</td><td>1.74</td><td>51.65</td></tr><tr align=center><td bgcolor='#d0d0d0'>CI任务的平均执行时间/min</td><td>68.33</td><td>50.64</td><td>14.25</td><td>13.41</td><td>18.12</td><td>27.17</td><td>85.36</td><td>34.91</td><td>7.30</td></tr><tr align=center><td bgcolor='#d0d0d0'>平均编译时间/min</td><td>21.28</td><td>13.90</td><td>7.40</td><td>3.30</td><td>5.76</td><td>6.08</td><td>35.68</td><td>22.87</td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均单测时间/min</td><td>50.01</td><td>38.13</td><td class='first'></td><td class='first'></td><td>13.56</td><td>20.04</td><td>54.81</td><td>12.81</td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均测试预测库时间/min</td><td class='first'></td><td class='first'></td><td>1.81</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均测试训练库时间/min</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均预测库大小/M</td><td class='first'></td><td class='first'></td><td>255.85</td><td class='first'></td><td class='first'></td><td class='first'></td><td>213.95</td><td>1224.21</td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均whl大小/M</td><td>296.93</td><td>136.59</td><td class='first'></td><td>143.63</td><td class='first'></td><td class='first'></td><td>103.96</td><td>49.34</td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均build目录大小/G</td><td>21.43</td><td>11.29</td><td class='first'></td><td>7.68</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>单测总数/个</td><td>1207.52</td><td>1151.87</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>单卡case总数/个</td><td>1128.08</td><td>1064.70</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>单卡case执行时间/min</td><td>37.31</td><td>21.18</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td>54.81</td><td>12.81</td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>多卡case总数/个</td><td>19.52</td><td>20.94</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>多卡case执行时间/min</td><td>2.97</td><td>1.85</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>独占case总数/个</td><td>59.92</td><td>66.23</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>独占case执行时间/min</td><td>9.73</td><td>12.80</td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td><td class='first'></td></tr><tr align=center><td bgcolor='#d0d0d0'>平均失败率</td><td>44.81</td><td>31.88</td><td>7.69</td><td>36.03</td><td>26.79</td><td>25.00</td><td>22.62</td><td>30.28</td><td>66.67</td></tr><tr align=center><td bgcolor='#d0d0d0'>平均rerun率</td><td>18.40</td><td>6.99</td><td>1.28</td><td>6.88</td><td>3.02</td><td>1.19</td><td>35.08</td><td>5.98</td><td>24.24</td></tr>"

    sendMail(before_7Days, zeroToday, MailContent)


main()
