# -*- coding: utf-8 -*-
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
            'ccacheRate', 'buildSize', 'WhlSize', 'testCaseCount_total',
            'fluidInferenceSize'
        ]
        self.requiredCIName = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Build', 'PR-CE-Framework',
            'PR-CI-ScienceTest', 'PR-CI-OP-benchmark', 'PR-CI-Model-benchmark',
            'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS',
            'PR-CI-Windows-Inference', 'PR-CI-Static-Check', 'PR-CI-Inference',
            'PR-CI-Mac-Python3', 'PR-CI-CINN', 'PR-CI-GpuPS', 'PR-CI-NPU',
            'PR-CI-APPROVAL', 'PR-CI-ROCM-Compile', 'PR-CI-Kunlun'
        ]
        self.keyIndexDict_ALL = {
            "00任务90分位耗时(排队+执行)/min": "consum_time_all_commit_time_point_90",
            "01任务90分位等待时间/min":
            "wait_time_all_commit_time_point_90",  #触发前的前一个任务的90分位耗时+自己的等待时间
            "02触发前的前一个任务的90分位耗时/min":
            "consum_time_lastjob_all_commit_mean_time_90",
            "03CPU 90分位等待时间/min": "cpu_wait_time_all_commit_time_point_90",
            "04GPU 90分位等待时间/min": "gpu_wait_time_all_commit_time_point_90",
            "05任务90分位执行时间/min": "exec_time_all_commit_time_point_90",
            "06CPU 90分位执行时间/min": "cpu_exec_time_all_commit_time_point_90",
            "07GPU 90分位执行时间/min": "gpu_exec_time_all_commit_time_point_90",
            "0890分位编译时间/min": "buildTime_all_commit_time_point_90",
            "09平均编译时间/min": "buildTime_all_commit_mean_time",
            "1090分位测试时间/min": "testCaseTime_total_all_commit_time_point_90",
            "11平均测试时间/min": "testCaseTime_total_all_commit_mean_time",
            "12平均失败率/%": "failRate_all_commit",
            "13平均rerun率/%": "rerunRate_all_commit",

            #"14任务平均耗时(排队+执行)/min": "consum_time_all_commit_mean_time",
            #"15任务平均等待时间/min": "wait_time_all_commit_mean_time", #触发前的前一个任务的平均耗时#+自己的等待时间
            #"16触发前的前一个任务的平均耗时/min": "consum_time_lastjob_all_commit_mean_time", 
            #"17CPU平均等待时间/min": "cpu_wait_time_all_commit_mean_time",
            #"15GPU平均等待时间/min": "gpu_wait_time_all_commit_mean_time",
            #"16任务平均执行时间/min": "exec_time_all_commit_mean_time",
            #"17CPU平均执行时间/min": "cpu_exec_time_all_commit_mean_time",
            #"18GPU平均执行时间/min": "gpu_exec_time_all_commit_mean_time",
        }
        self.ciExecTimeLastJob = {
            'PR-CI-Build': 'PR-CI-Py3',
            'PR-CI-Coverage': 'PR-CI-Py3',
            'PR-CI-GpuPS': 'PR-CI-Py3',
            'PR-CI-CINN': 'PR-CI-Py3',
            'PR-CI-Static-Check': 'PR-CI-Py3',
            'PR-CE-Framework': 'PR-CI-Build',
            'PR-CI-ScienceTest': 'PR-CI-Build',
            'PR-CI-OP-benchmark': 'PR-CI-Build',
            'PR-CI-Model-benchmark': 'PR-CI-Build'
        }
        self.keyIndexDict_success = {
            "07成功任务90分位耗时(排队+执行)/min":
            "consum_time_success_commit_time_point_90",
            "08成功任务90分位等待时间/min": "wait_time_success_commit_time_point_90",
            "09成功任务CPU 90分位等待时间/min":
            "cpu_wait_time_success_commit_time_point_90",
            "10成功任务GPU 90分位等待时间/min":
            "gpu_wait_time_success_commit_time_point_90",
            "11成功任务90分位执行时间/min": "exec_time_success_commit_time_point_90",
            "12成功任务CPU 90分位执行时间/min":
            "cpu_exec_time_success_commit_time_point_90",
            "13成功任务GPU 90分位执行时间/min":
            "gpu_exec_time_success_commit_time_point_90",
            "14成功任务90分位编译时间/min": "buildTime_success_commit_time_point_90",
            "15成功任务90分位测试时间/min":
            "testCaseTime_total_success_commit_time_point_90",
            "16成功任务平均编译时间/min": "buildTime_success_commit_mean_time",
            "17成功任务平均测试时间/min": "testCaseTime_total_success_commit_mean_time",
        }
        self.keyIndexDict_Part = {
            "01任务90分位等待时间/min": "wait_time_all_commit_time_point_90",
            "03CPU 90分位等待时间/min": "cpu_wait_time_all_commit_time_point_90",
            "05GPU 90分位等待时间/min": "gpu_wait_time_all_commit_time_point_90",
            "07任务90分位执行时间/min": "exec_time_all_commit_time_point_90",
            "09CPU 90分位执行时间/min": "cpu_exec_time_all_commit_time_point_90",
            "11GPU 90分位执行时间/min": "gpu_exec_time_all_commit_time_point_90",
            "12平均编译时间/min": "buildTime_mean_time_all_commit",
            "13平均测试时间/min": "testCaseTime_total_mean_time_all_commit",
        }

        self.repo = ['PaddlePaddle/Paddle']  #, 'PaddlePaddle/docs']

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
            ci_index[ci] = {}
            if ci == 'PR-CI-Windows':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/' % ci
            else:
                queryCIName = 'ciName =~ /^%s/' % ci
            #all-commit 
            for key in sorted(self.keyIndexDict_ALL):
                if '触发前的前一个任务' in key and startTime_stamp > 1646668800:
                    if ci in self.ciExecTimeLastJob:
                        lastJob = self.ciExecTimeLastJob[ci]
                        if '触发前的前一个任务的90分位耗时' in key:
                            query_stat = "select mean(consum_time_all_commit_time_point_90) from paddle_ci_aggregation_by_day where ciName =~ /^%s/ and commit_createTime >= %s and commit_createTime < %s" % (
                                lastJob, startTime_stamp, endTime_stamp)
                        elif '触发前的前一个任务的平均耗时' in key:
                            query_stat = "select mean(consum_time_all_commit_mean_time) from paddle_ci_aggregation_by_day where ciName =~ /^%s/ and commit_createTime >= %s and commit_createTime < %s" % (
                                lastJob, startTime_stamp, endTime_stamp)
                        key = key[2:]
                        result = self.db.queryDB(query_stat, 'mean')
                        ci_index[ci][
                            key] = "%.2f" % result if result != None else None
                    else:
                        continue
                else:
                    query_key = self.keyIndexDict_ALL[key]
                    key = key[2:]
                    query_stat = "select mean(%s) from paddle_ci_aggregation_by_day where %s and commit_createTime >= %s and commit_createTime < %s" % (
                        query_key, queryCIName, startTime_stamp, endTime_stamp)
                    result = self.db.queryDB(query_stat, 'mean')
                    ci_index[ci][
                        key] = "%.2f" % result if result != None else None

            if startTime_stamp > 1646668800 and ci in self.ciExecTimeLastJob:
                ci_index[ci]['任务90分位等待时间/min'] = round(
                    (float(ci_index[ci]['任务90分位等待时间/min']) +
                     float(ci_index[ci]['触发前的前一个任务的90分位耗时/min'])), 2)
                ci_index[ci]['任务90分位耗时(排队+执行)/min'] = round(
                    (float(ci_index[ci]['任务90分位耗时(排队+执行)/min']) +
                     float(ci_index[ci]['触发前的前一个任务的90分位耗时/min'])), 2)

                #ci_index[ci]['任务平均等待时间/min'] = round((float(ci_index[ci]['任务平均等待时间/min']) + float(ci_index[ci]['触发前的前一个任务的平均耗时/min'])), 2)
                #ci_index[ci]['任务平均耗时(排队+执行)/min'] = round((float(ci_index[ci]['任务平均耗时(排队+执行)/min']) + float(ci_index[ci]['触发前的前一个任务的平均耗时/min'])), 2)

            #success-commit 
            for key in sorted(self.keyIndexDict_success):
                query_key = self.keyIndexDict_success[key]
                key = key[2:]
                query_stat = "select mean(%s) from paddle_ci_aggregation_by_day where %s and commit_createTime >= %s and commit_createTime < %s" % (
                    query_key, queryCIName, startTime_stamp, endTime_stamp)
                result = self.db.queryDB(query_stat, 'mean')
                ci_index[ci][key] = "%.2f" % result if result != None else None

            #详细指标
            for index in self.countTypeCIindex:
                query_stat = "select mean(%s) from paddle_ci_index where %s and createTime > %s and createTime < %s" % (
                    index, queryCIName, startTime_stamp, endTime_stamp)
                average_value = self.db.queryDB(query_stat, 'mean')
                key = '%s' % index
                ci_index[ci][
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

            ci_index[ci]['rerunRate'] = "%.2f" % (
                (1 - noRepeat_commitCount / all_commitCount) *
                100) if all_commitCount != None else 0

            #失败率
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and status='failure' and commit_createTime > %s and commit_createTime < %s and time > '2020-07-09 07:40:00'" % (
                queryCIName, startTime_stamp, endTime_stamp)
            fail_commitCount = self.db.queryDB(fail_commitCount_query_stat,
                                               'count')
            ci_index[ci]['failRate'] = "%.2f" % (
                (fail_commitCount /
                 all_commitCount) * 100) if fail_commitCount != None else 0

        return ci_index

    def getRerunRatio(self, startTime, endTime):
        """获取由于单测随机挂引起的rerun率"""
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        rerun_index = {}
        all_testfailed_rerunRatio = 0.0
        for ci in self.ciNameHasTests:
            print("ci: %s" % ci)
            rerunCount = {}
            count = 0
            if ci == 'PR-CI-Mac':
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            elif ci == 'PR-CI-Windows':
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/ and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            elif ci == 'PR-CI-Coverage':
                ALL_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Coverage-compile-Daily/ and ciName !~ /^PR-CI-Coverage-Eager-Test/ and commit_createTime > %s and commit_createTime < %s" % (
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
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            elif ci == 'PR-CI-Coverage':
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Coverage-compile-Daily/ and ciName !~ /^PR-CI-Coverage-Eager-Test/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s " % (
                    ci, startTime_stamp, endTime_stamp)
            else:
                query_stat = "SELECT commitId from paddle_ci_status where ciName =~ /^%s/ and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s" % (
                    ci, startTime_stamp, endTime_stamp)
            query_stat = "SELECT commitId,PR from paddle_ci_status where ciName='%s' and status='failure' and EXCODE=8 and commit_createTime > %s and commit_createTime < %s and time > '2020-07-13 14:20:00'" % (
                ci, startTime_stamp, endTime_stamp)
            print(query_stat)
            result = list(self.db.query(query_stat))
            if len(result) == 0:
                rerun_index['%s_testfailed_rerunRatio' % ci] = 0
            else:
                for key in result[0]:
                    print(key)
                    commitId = key['commitId']
                    #PR = key['PR']
                    '''
                    if '%s_%s' %(PR, commitId) not in rerunCount:
                        rerunCount['%s_%s' %(PR, commitId)] = 1
                    else:
                        value = rerunCount['%s_%s' %(PR, commitId)]
                        value += 1
                        rerunCount['%s_%s' %(PR, commitId)] = value
                    '''
                    if commitId not in rerunCount:
                        rerunCount[commitId] = 1
                    else:
                        value = rerunCount[commitId]
                        value += 1
                        rerunCount[commitId] = value
            for commitId in rerunCount:
                if rerunCount[commitId] > 1:
                    #print("%s: %s" %(commitId, rerunCount[commitId]))
                    count += (rerunCount[commitId] - 1)
            rerun_index['%s_testfailed_rerunRatio' % ci] = '%.2f' % (
                count / ALL_commitCount * 100)
            all_testfailed_rerunRatio += float(rerun_index[
                '%s_testfailed_rerunRatio' % ci])
        rerun_index[
            'all_testfailed_rerunRatio'] = '%.2f' % all_testfailed_rerunRatio
        return rerun_index

    def getRerunData(self, startTime, endTime):
        """分析rerun原因"""
        rerunMessage_dict = {}
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        for ci in self.requiredCIName:
            rerunMessage_dict[ci] = {}
            if ci == 'PR-CI-Windows':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/' % ci
            elif ci == 'PR-CI-Coverage':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Coverage-compile-Daily/ and ciName !~ /^PR-CI-Coverage-Eager-Test/' % ci
            else:
                queryCIName = 'ciName =~ /^%s/' % ci

            query_stat = "select commitId,status,EXCODE,PR,triggerUser from paddle_ci_status where repo='PaddlePaddle/Paddle' and %s and commit_createTime>%s and commit_createTime<%s " % (
                queryCIName, startTime_stamp, endTime_stamp)
            res = list(self.db.query(query_stat))
            result = {}
            for index in res[0]:
                t = {
                    'time': index['time'],
                    'PR': index['PR'],
                    'triggerUser': index['triggerUser'],
                    'status': index['status'],
                    'EXCODE': index['EXCODE']
                }
                if index['commitId'] not in result:
                    result[index['commitId']] = []

                result[index['commitId']].append(t)
            all_commit_count = len(res[0])
            rerun_success_count = 0
            rerun_success_count_testfailed = 0
            rerun_success_count_buildfailed = 0
            rerun_success_count_networkfailed = 0
            cov_label_success_count = 0  #覆盖率不够。标记成功的
            rerun_success = []
            for key in result:
                if len(result[key]) > 1:
                    if result[key][-1]['status'] == 'success':
                        if result[key][-1]['EXCODE'] == 0:
                            rerun_success_count += len(result[key]) - 1
                            if result[key][-2]['EXCODE'] == 7:
                                rerun_success_count_buildfailed += len(result[
                                    key]) - 1
                            elif result[key][-2]['EXCODE'] == 8:
                                rerun_success_count_testfailed += len(result[
                                    key]) - 1
                            elif result[key][-2]['EXCODE'] == 503:
                                rerun_success_count_networkfailed += len(
                                    result[key]) - 1
                        elif result[key][-1]['EXCODE'] == 9:
                            cov_label_success_count += len(result[key]) - 1
            noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s" % (
                queryCIName, startTime_stamp, endTime_stamp)
            noRepeat_commitCount = self.db.queryDB(
                noRepeat_commitCount_query_stat, 'count')
            rerunMessage_dict[ci]['rerunRatio'] = '%.2f' % (
                (1 - noRepeat_commitCount / all_commit_count) * 100)
            rerunMessage_dict[ci]['rerunRatio_success'] = '%.2f' % (
                (rerun_success_count / all_commit_count) * 100)
            rerunMessage_dict[ci][
                'rerunRatio_success_by_buildfailed'] = '%.2f' % (
                    (rerun_success_count_buildfailed / all_commit_count) * 100)
            rerunMessage_dict[ci][
                'rerunRatio_success_by_testfailed'] = '%.2f' % (
                    (rerun_success_count_testfailed / all_commit_count) * 100)
            rerunMessage_dict[ci][
                'rerunRatio_success_by_networkfailed'] = '%.2f' % (
                    (rerun_success_count_networkfailed /
                     all_commit_count) * 100)
            if ci == 'PR-CI-Coverage':
                rerunMessage_dict[ci]['cov_label_success'] = '%.2f' % (
                    (cov_label_success_count / all_commit_count) * 100)
            else:
                rerunMessage_dict[ci]['cov_label_success'] = '/'
        return rerunMessage_dict

    def getUserPerceptionIndexAndRerunByTestsFailed(self,
                                                    ciIndex_thisWeek,
                                                    ciIndex_lastWeek=None):
        """
        表1: 感知指标: 
        1. 任务量变化
        2. 所有commit从提交到返回的90分位耗时
        """
        rise_red_color = "<td bgcolor='#ff6eb4'>"
        decline_green_color = "<td bgcolor='#b5c4b1'>"
        UserPerceptionIndexContent = "<table border='1' align=center> <caption><font size='3'><b>感知指标</b></font></caption>"
        #任务量变化
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI任务量/个</td>"
        DIFF_RATE = "%.2f" % float(
            abs(ciIndex_thisWeek['Paddle_commitCount'] - ciIndex_lastWeek[
                'Paddle_commitCount']) /
            ciIndex_lastWeek['Paddle_commitCount'] * 100)
        if float(DIFF_RATE) > 20:
            UserPerceptionIndexContent += "%s %s->%s(↑ %s" % (
                rise_red_color, ciIndex_lastWeek['Paddle_commitCount'],
                ciIndex_thisWeek['Paddle_commitCount'], DIFF_RATE
            ) if ciIndex_thisWeek['Paddle_commitCount'] - ciIndex_lastWeek[
                'Paddle_commitCount'] > 0 else "%s %s->%s(↓ %s" % (
                    decline_green_color,
                    ciIndex_lastWeek['Paddle_commitCount'],
                    ciIndex_thisWeek['Paddle_commitCount'], DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s->%s(↑ %s" % (
                ciIndex_lastWeek['Paddle_commitCount'],
                ciIndex_thisWeek['Paddle_commitCount'], DIFF_RATE
            ) if ciIndex_thisWeek['Paddle_commitCount'] - ciIndex_lastWeek[
                'Paddle_commitCount'] > 0 else "<td>%s->%s(↓ %s" % (
                    ciIndex_lastWeek['Paddle_commitCount'],
                    ciIndex_thisWeek['Paddle_commitCount'], DIFF_RATE)

        UserPerceptionIndexContent += "%)</td></tr>"

        #所有commit从提交到返回结果90分位耗时
        UserPerceptionIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI任务从提交到返回结果90分位耗时/min</td>"
        thisweek_max_consumtime_all_commit = 0
        lastweek_max_consumtime_all_commit = 0
        for ci in self.requiredCIName:
            print("ci:%s" % ci)
            thisweek_max_consumtime_ci_all_commit = float(ciIndex_thisWeek[ci][
                '任务90分位耗时(排队+执行)/min']) if ciIndex_thisWeek[ci][
                    '任务90分位耗时(排队+执行)/min'] != None else 0
            lastweek_max_consumtime_ci_all_commit = float(ciIndex_lastWeek[ci][
                '任务90分位耗时(排队+执行)/min']) if ciIndex_lastWeek[ci][
                    '任务90分位耗时(排队+执行)/min'] != None else 0

            if thisweek_max_consumtime_ci_all_commit > thisweek_max_consumtime_all_commit:
                thisweek_max_consumtime_all_commit = thisweek_max_consumtime_ci_all_commit
                thisweek_max_consumtime_ci = ci
            if lastweek_max_consumtime_ci_all_commit > lastweek_max_consumtime_all_commit:
                lastweek_max_consumtime_all_commit = lastweek_max_consumtime_ci_all_commit
                lastweek_max_consumtime_ci = ci

        DIFF_RATE = "%.2f" % float(
            abs(thisweek_max_consumtime_all_commit -
                lastweek_max_consumtime_all_commit) /
            lastweek_max_consumtime_all_commit * 100)
        if float(DIFF_RATE) > 20:
            UserPerceptionIndexContent += "%s %s->%s(↑ %s" % (
                rise_red_color, lastweek_max_consumtime_all_commit,
                thisweek_max_consumtime_all_commit, DIFF_RATE
            ) if thisweek_max_consumtime_all_commit - lastweek_max_consumtime_all_commit > 0 else "%s %s->%s(↓ %s" % (
                decline_green_color, lastweek_max_consumtime_all_commit,
                thisweek_max_consumtime_all_commit, DIFF_RATE)
        else:
            UserPerceptionIndexContent += "<td>%s->%s(↑ %s" % (
                lastweek_max_consumtime_all_commit,
                thisweek_max_consumtime_all_commit, DIFF_RATE
            ) if thisweek_max_consumtime_all_commit - lastweek_max_consumtime_all_commit > 0 else "<td>%s->%s(↓ %s" % (
                lastweek_max_consumtime_all_commit,
                thisweek_max_consumtime_all_commit, DIFF_RATE)
        UserPerceptionIndexContent += "%)</td></tr></table>"

        return UserPerceptionIndexContent

    def getKeyIndex(self, indexType, ciIndex_thisWeek, ciIndex_lastWeek=None):
        """
        获取指标
        indexType == keyIndexDict_ALL，代表所有任务的指标
        indexType == keyIndexDict_success，代表成功任务的指标
        """
        if indexType == 'keyIndexDict_ALL':
            KeyIndexContent = "<table border='1' align=center> <caption><font size='3'><b>关键指标</b></font></caption>"
            keyIndexDict = self.keyIndexDict_ALL
        elif indexType == 'keyIndexDict_success':
            KeyIndexContent = "<table border='1' align=center> <caption><font size='3'><b>成功任务CI指标</b></font></caption>"
            keyIndexDict = self.keyIndexDict_success
        startTime = ciIndex_thisWeek['startTime']
        endTime = ciIndex_thisWeek['endTime']
        KeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            KeyIndexContent += "<td>%s</td>" % ci
        KeyIndexContent += "</tr>"

        for index in sorted(keyIndexDict):
            index = index[2:]
            if index == '平均rerun率/%':
                index = 'rerunRate'
            elif index == '平均失败率/%':
                index = 'failRate'
            if ciIndex_lastWeek == None:
                KeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>%s(本周值)</td>" % index
                for ci in self.requiredCIName:
                    if index not in ciIndex_thisWeek[ci] or ciIndex_thisWeek[
                            ci][index] == None:
                        KeyIndexContent += "<td> / </td>"
                        continue

                    value = '%s' % ciIndex_thisWeek[ci][index]
                    KeyIndexContent += "<td>{}</td>".format(value)
            else:
                KeyIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>%s(本周值|上周值|浮动)</td>" % index
                for ci in self.requiredCIName:
                    if index not in ciIndex_thisWeek[ci]:
                        KeyIndexContent += "<td> / </td>"
                        continue
                    if ciIndex_thisWeek[ci][
                            index] == None and ciIndex_lastWeek[ci][
                                index] == None:
                        KeyIndexContent += "<td> / </td>"
                        continue
                    if ciIndex_thisWeek[ci][
                            index] == None and ciIndex_lastWeek[ci][
                                index] != None:
                        KeyIndexContent += "<td>None | %s</td>" % ciIndex_lastWeek[
                            ci][index]
                        continue
                    if ciIndex_thisWeek[ci][
                            index] != None and ciIndex_lastWeek[ci][
                                index] == None:
                        KeyIndexContent += "<td>%s | None</td>" % ciIndex_thisWeek[
                            ci][index]
                        continue

                    thisWeek_lastWeek_radio = float(
                        (float(ciIndex_thisWeek[ci][index]) -
                         float(ciIndex_lastWeek[ci][index])) /
                        float(ciIndex_lastWeek[ci][index])
                    ) if ciIndex_lastWeek[ci][index] != 0 else float(
                        (float(ciIndex_thisWeek[ci][index]) - 0.00001
                         )) / 0.00001
                    value = '%s | %s' % (ciIndex_thisWeek[ci][index],
                                         ciIndex_lastWeek[ci][index])
                    if thisWeek_lastWeek_radio >= 0:
                        value = value + ' |↑%.2f' % (thisWeek_lastWeek_radio *
                                                     100) + '%'
                        standard_radio = 0.05
                        if thisWeek_lastWeek_radio >= standard_radio:
                            KeyIndexContent += "<td bgcolor='#ff6eb4'>{}</td>".format(
                                value)
                        else:
                            KeyIndexContent += "<td>{}</td>".format(value)
                    elif thisWeek_lastWeek_radio < 0:
                        value = value + ' |↓%.2f' % (
                            abs(thisWeek_lastWeek_radio) * 100) + '%'
                        standard_radio = 0.05
                        if thisWeek_lastWeek_radio <= -standard_radio:
                            KeyIndexContent += "<td bgcolor='#b5c4b1'>{}</td>".format(
                                value)
                        else:
                            KeyIndexContent += "<td>{}</td>".format(value)

        KeyIndexContent += "</tr></table>"
        return KeyIndexContent

    def getInternalDetailIndex(self, ciIndex_thisWeek, ciIndex_lastWeek=None):
        """获取内部本周详细指标"""
        InternalDetailIndexContent = "<table border='1' align=center> <caption><font size='3'><b>对内详细指标</b></font></caption>"
        ci_index_dic = {
            "00CPU平均等待时间/min": "cpu_wait_time_all_commit", "01CPU平均执行时间/min": "cpu_exec_time_all_commit",
            "02GPU平均等待时间/min": "gpu_wait_time_all_commit", "03GPU平均执行时间/min": "gpu_exec_time_all_commit",
            "04平均执行时间/min": "exec_time_all_commit",  "05平均排队时间/min": "wait_time_all_commit",
            "06平均耗时（排队+执行）/min": "consum_time_all_commit",
            "07平均编译时间/min": "buildTime_all_commit", "08平均ccache命中率/%": "ccacheRate",
            "09平均单测时间/min": "testCaseTime_total_all_commit", "10单卡case平均执行时间/min": "testCaseTime_single",\
            "11多卡case平均执行时间/min": "testCaseTime_multi", "12独占case平均执行时间/min": "testCaseTime_exclusive",
            "13case总数/个": "testCaseCount_total", "14单卡case总数/个": "testCaseCount_single",
            "15多卡case总数/个": "testCaseCount_multi", "16独占case总数/个": "testCaseCount_exclusive",
            "17平均whl大小/M": "WhlSize", "18平均build目录大小/G": "buildSize",
            "19平均rerun率": "rerunRate", "20平均失败率": "failRate",
            "21平均预测库大小/M": "fluidInferenceSize", "22平均测试预测库时间/min": "testFluidLibTime",
            "23平均测试训练库时间/min": "testFluidLibTrainTime",
            "24成功任务的CPU平均等待时间/min": "cpu_wait_time_success_commit", "25成功任务的CPU平均执行时间/min": "cpu_exec_time_success_commit",
            "26成功任务的GPU平均等待时间/min": "gpu_wait_time_all_commit", "27成功任务的GPU平均执行时间/min": "gpu_exec_time_all_commit",
            "28成功任务的平均等待时间/min": "wait_time_success_commit", "29成功任务的平均执行时间/min": "exec_time_success_commit",
            "30成功任务的平均耗时（排队+执行）/min": "consum_time_success_commit", "31成功任务的平均编译时间/min": "buildTime_success_commit",
            "32成功任务的平均单测时间/min": "testCaseTime_total_success_commit"}

        ci_index_key_list = sorted(ci_index_dic.keys())
        InternalDetailIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            InternalDetailIndexContent += "<td>{}</td>".format(ci)
        InternalDetailIndexContent += "</tr>"
        THISWEEK_CI_INDEX_INFO = ""
        for i in range(len(ci_index_dic)):
            key = ci_index_key_list[i][2:]
            #print(key)
            InternalDetailIndexContent += "<tr align=center><td bgcolor='#d0d0d0'>{}</td>".format(
                key)
            for ci_name in self.requiredCIName:
                key = ci_index_dic[ci_index_key_list[i]]
                if key not in ciIndex_thisWeek[ci_name]:
                    InternalDetailIndexContent += "<td>{}</td>".format('-')
                else:
                    value = ciIndex_thisWeek[ci_name][key]
                    value = '-' if value == None else value
                    InternalDetailIndexContent += "<td>{}</td>".format(value)
            InternalDetailIndexContent += "</tr>"
        print(InternalDetailIndexContent)
        return InternalDetailIndexContent

    def getExcodeIndex(self, startTime, endTime):
        """失败原因分析"""
        startTime_stamp = self.common.strTimeToTimestamp(startTime)
        endTime_stamp = self.common.strTimeToTimestamp(endTime)
        exCodeContent = "<table border='1' align=center> <caption><font size='3'><b>CI失败原因占比</b></font></caption>"
        exCodeContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        failed_dic = {}
        for ci in self.requiredCIName:
            failed_dic[ci] = {}
            exCodeContent += "<td>{}</td>".format(ci)
            if ci == 'PR-CI-Windows':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/' % ci
            else:
                queryCIName = 'ciName =~ /^%s/' % ci
            fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                queryCIName, startTime_stamp, endTime_stamp)
            fail_commitCount = self.db.queryDB(fail_commitCount_query_stat,
                                               'count')

            all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and commit_createTime > %s and commit_createTime < %s " % (
                queryCIName, startTime_stamp, endTime_stamp)
            all_commitCount = self.db.queryDB(all_commitCount_query_stat,
                                              'count')

            failRate = fail_commitCount / all_commitCount * 100
            failed_dic[ci]['failRate'] = failRate
            failed_dic[ci]['all_commitCount'] = all_commitCount
            failed_dic[ci]['fail_commitCount'] = fail_commitCount

        for i in self.exCodeDict:
            exCodeContent += "<tr align=center><td bgcolor='#d0d0d0'>%s</td>" % i
            for ci in self.requiredCIName:
                all_commitCount = failed_dic[ci]['all_commitCount']
                excode = self.exCodeDict[i]
                if ci == 'PR-CI-Windows':
                    queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/' % ci
                else:
                    queryCIName = 'ciName =~ /^%s/' % ci
                excode_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where %s and EXCODE=%s and status='failure' and commit_createTime > %s and commit_createTime < %s " % (
                    queryCIName, excode, startTime_stamp, endTime_stamp)

                excode_commitCount = self.db.queryDB(excode_query_stat,
                                                     'count')
                excode_ratio = '%.2f' % (
                    excode_commitCount / all_commitCount * 100
                ) + '%' if excode_commitCount != None else '/'
                exCodeContent += "<td>{}</td>".format(excode_ratio)
            exCodeContent += "</tr>"
        exCodeContent += "</table>"
        return exCodeContent

    def getRerunIndex(self, startTime, endTime):
        """rerun原因分类表"""
        rerunMessage_dict = self.getRerunData(startTime, endTime)
        rerun_dict = {
            "0rerunRatio": "整体rerun率",
            "1rerunRatio_success": "rerun后成功占比",
            "2rerunRatio_success_by_buildfailed": "编译失败但rerun成功占比",
            "3rerunRatio_success_by_testfailed": "单测失败但rerun成功占比",
            "4rerunRatio_success_by_networkfailed": "网络失败但rerun成功占比",
            "5cov_label_success": "rerun后因覆盖率不够标记成功占比"
        }
        rerunContent = "<table border='1' align=center> <caption><font size='3'><b>CI rerun原因占比</b></font></caption>"
        rerunContent += "<tr align=center><td bgcolor='#d0d0d0'>CI名称</td>"
        for ci in self.requiredCIName:
            rerunContent += "<td>{}</td>".format(ci)
        rerunContent += "</tr>"

        for index in sorted(rerun_dict):
            rerunContent += "<tr align=center><td>{}</td>".format(rerun_dict[
                index])
            index = index[1:]
            for ci in self.requiredCIName:
                rerunContent += "<td>{}</td>".format(rerunMessage_dict[ci][
                    index])
            rerunContent += "</tr>"
        rerunContent += '</table>'
        return rerunContent


def sendMail(startTime, endTime, Content):
    mail = Mail()
    mail.set_sender('xxx@baidu.com')
    mail.set_receivers(['xxxx@baidu.com'])
    mail.set_title('%s~%s Paddle CI评价指标统计' % (startTime, endTime))
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
    #昨天0点
    before_1Days = zeroToday - datetime.timedelta(days=1)
    zeroToday = now - datetime.timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond)
    #7天前0点
    before_7Days = zeroToday - datetime.timedelta(days=8)
    print(before_7Days)
    #14天前0点
    before_14Days = zeroToday - datetime.timedelta(days=15)

    WeeklyCI = WeeklyCIIndex()

    ciIndex_thisWeek = WeeklyCI.getWeeklyCIIndex(
        str(before_7Days), str(before_1Days))
    #print("ciIndex_thisWeek: %s" %ciIndex_thisWeek)
    ciIndex_lastWeek = WeeklyCI.getWeeklyCIIndex(
        str(before_14Days), str(before_7Days))
    #print("ciIndex_lastWeek: %s" %ciIndex_lastWeek)

    UserPerceptionIndexContent = WeeklyCI.getUserPerceptionIndexAndRerunByTestsFailed(
        ciIndex_thisWeek, ciIndex_lastWeek)
    InternalKeyIndexContent = WeeklyCI.getKeyIndex(
        'keyIndexDict_ALL', ciIndex_thisWeek, ciIndex_lastWeek)
    rerunContent = WeeklyCI.getRerunIndex(
        '%s 00:00:00' % ciIndex_thisWeek['startTime'],
        '%s 00:00:00' % ciIndex_thisWeek['endTime'])
    exCodeContent = WeeklyCI.getExcodeIndex(
        '%s 00:00:00' % ciIndex_thisWeek['startTime'],
        '%s 00:00:00' % ciIndex_thisWeek['endTime'])

    MailContent = "<html><body><p>Hi, ALL:</p> <p>本周(%s 00:00:00 ~ %s 00:00:00)CI评价指标详细信息可参考如下表格:</p> <p>CI评价指标的计算方式可见: http://agroup.baidu.com/paddle-ci/md/article/3352500</p>" % (
        ciIndex_thisWeek['startTime'], ciIndex_thisWeek['endTime'])
    MailContent += UserPerceptionIndexContent
    MailContent += InternalKeyIndexContent
    MailContent += rerunContent
    MailContent += exCodeContent
    print('MailContent')
    print(MailContent)

    sendMail(before_7Days, before_1Days, MailContent)


main()
