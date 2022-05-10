import sys
sys.path.append("..")
from utils.db import Database
from utils.common import CommonModule
import datetime
import time
import numpy as np
import math


class ciIndex_dataAggregation():
    """CI指标的数据聚合"""

    def __init__(self, queryTime):
        self.required_ci_list = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Build', 'PR-CE-Framework',
            'PR-CI-ScienceTest', 'PR-CI-OP-benchmark', 'PR-CI-Model-benchmark',
            'PR-CI-Static-Check', 'PR-CI-infrt', 'PR-CI-CINN',
            'PR-CI-Inference', 'PR-CI-GpuPS', 'PR-CI-NPU', 'PR-CI-Mac-Python3',
            'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS',
            'PR-CI-Windows-Inference', 'PR-CI-APPROVAL', 'PR-CI-ROCM-Compile',
            'PR-CI-Kunlun'
        ]
        self.ciNameWithCPU = [
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Build', 'PR-CI-Static-Check',
            'PR-CI-infrt', 'PR-CI-CINN', 'PR-CI-Inference', 'PR-CI-GpuPS',
            'PR-CI-NPU', 'PR-CI-MLU'
        ]
        self.ciNameWithGPU = [
            'PR-CI-Coverage', 'PR-CE-Framework', 'PR-CI-ScienceTest',
            'PR-CI-OP-benchmark', 'PR-CI-Model-benchmark',
            'PR-CI-Static-Check', 'PR-CI-infrt', 'PR-CI-CINN',
            'PR-CI-Inference', 'PR-CI-NPU'
        ]
        self.ciNameReuseOutput = [
            'PR-CE-Framework', 'PR-CI-ScienceTest', 'PR-CI-OP-benchmark',
            'PR-CI-Model-benchmark'
        ]
        self.db = Database()
        self.common = CommonModule()
        self.detailTimeIndex = ['buildTime', 'testCaseTime_total']
        self.startTime = self.common.strTimeToTimestamp(queryTime)
        self.endTime = self.startTime + 86400

    def time_EveryDayAggregation(self):
        ci_index = {}
        for ci in self.required_ci_list:
            ci_index[ci] = {}
            if ci == 'PR-CI-Windows':
                queryCIName = 'ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/' % ci
            else:
                queryCIName = 'ciName =~ /^%s/' % ci

            #cpu阶段执行时间
            ## 4.1之前 没有commit_submitTime
            if ci in self.ciNameWithCPU:
                ###isrebuild 3.8开始有这个数据
                if ci in ['PR-CI-NPU']:  #无docker build time
                    if self.startTime > 1646668800:  #isrebuild 3.8开始有这个数据
                        cpu_wait_time_all_commit_query_stat = "select (paddle_build_startTime-commit_createTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                        cpu_wait_time_success_commit_query_stat = "select (paddle_build_startTime-commit_createTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and status='success' and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                    else:
                        cpu_wait_time_all_commit_query_stat = "select (paddle_build_startTime-commit_createTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0" % (
                            queryCIName, self.startTime, self.endTime)
                        cpu_wait_time_success_commit_query_stat = "select (paddle_build_startTime-commit_createTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and status='success'" % (
                            queryCIName, self.startTime, self.endTime)
                else:
                    if self.startTime > 1646668800:  #isrebuild 3.8开始有这个数据
                        cpu_wait_time_all_commit_query_stat = "select (paddle_build_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                        cpu_wait_time_success_commit_query_stat = "select (paddle_build_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and status='success' and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                    else:
                        cpu_wait_time_all_commit_query_stat = "select (paddle_build_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0" % (
                            queryCIName, self.startTime, self.endTime)
                        cpu_wait_time_success_commit_query_stat = "select (paddle_build_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and status='success'" % (
                            queryCIName, self.startTime, self.endTime)
                #print(cpu_wait_time_all_commit_query_stat)
                cpu_wait_time_all_commit = self.data_handler(
                    cpu_wait_time_all_commit_query_stat)
                cpu_wait_time_success_commit = self.data_handler(
                    cpu_wait_time_success_commit_query_stat)
                ci_index[ci][
                    'cpu_wait_time_all_commit'] = cpu_wait_time_all_commit
                ci_index[ci][
                    'cpu_wait_time_success_commit'] = cpu_wait_time_success_commit

                cpu_exec_time_all_commit_query_stat = "select (paddle_build_endTime-paddle_build_startTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0" % (
                    queryCIName, self.startTime, self.endTime)
                cpu_exec_time_success_commit_query_stat = "select (paddle_build_endTime-paddle_build_startTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_build_startTime!=0 and status='success'" % (
                    queryCIName, self.startTime, self.endTime)
                cpu_exec_time_all_commit = self.data_handler(
                    cpu_exec_time_all_commit_query_stat)
                cpu_exec_time_success_commit = self.data_handler(
                    cpu_exec_time_success_commit_query_stat)
                ci_index[ci][
                    'cpu_exec_time_all_commit'] = cpu_exec_time_all_commit
                ci_index[ci][
                    'cpu_exec_time_success_commit'] = cpu_exec_time_success_commit

            if ci in self.ciNameWithGPU:
                if ci in self.ciNameReuseOutput:
                    if self.startTime > 1646668800:  #isrebuild 3.8开始有这个数据
                        gpu_wait_time_all_commit_query_stat = "select (paddle_test_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                        gpu_wait_time_success_commit_query_stat = "select (paddle_test_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and status='success' and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                    else:
                        gpu_wait_time_all_commit_query_stat = "select (paddle_test_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0" % (
                            queryCIName, self.startTime, self.endTime)
                        gpu_wait_time_success_commit_query_stat = "select (paddle_test_startTime-docker_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and status='success'" % (
                            queryCIName, self.startTime, self.endTime)
                else:
                    if self.startTime > 1646668800:  #isrebuild 3.8开始有这个数据
                        gpu_wait_time_all_commit_query_stat = "select (paddle_test_startTime-paddle_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                        gpu_wait_time_success_commit_query_stat = "select (paddle_test_startTime-paddle_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and status='success' and isRebuild=0" % (
                            queryCIName, self.startTime, self.endTime)
                    else:
                        gpu_wait_time_all_commit_query_stat = "select (paddle_test_startTime-paddle_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0" % (
                            queryCIName, self.startTime, self.endTime)
                        gpu_wait_time_success_commit_query_stat = "select (paddle_test_startTime-paddle_build_endTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and status='success'" % (
                            queryCIName, self.startTime, self.endTime)

                gpu_wait_time_all_commit = self.data_handler(
                    gpu_wait_time_all_commit_query_stat)
                gpu_wait_time_success_commit = self.data_handler(
                    gpu_wait_time_success_commit_query_stat)
                ci_index[ci][
                    'gpu_wait_time_all_commit'] = gpu_wait_time_all_commit
                ci_index[ci][
                    'gpu_wait_time_success_commit'] = gpu_wait_time_success_commit

                gpu_exec_time_all_commit_query_stat = "select (paddle_test_endTime-paddle_test_startTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0" % (
                    queryCIName, self.startTime, self.endTime)
                gpu_exec_time_all_commit = self.data_handler(
                    gpu_exec_time_all_commit_query_stat)
                ci_index[ci][
                    'gpu_exec_time_all_commit'] = gpu_exec_time_all_commit
                gpu_exec_time_success_commit_query_stat = "select (paddle_test_endTime-paddle_test_startTime)/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and paddle_test_startTime!=0 and status='success'" % (
                    queryCIName, self.startTime, self.endTime)
                gpu_exec_time_success_commit = self.data_handler(
                    gpu_exec_time_success_commit_query_stat)
                ci_index[ci][
                    'gpu_exec_time_success_commit'] = gpu_exec_time_success_commit

            #所有commit执行时间 (去除document_fix)
            average_exec_time_all_commit_query_stat = "select execTime_total/60 as t,* from paddle_ci_status where %s and documentfix='False' and commit_createTime >= %s and commit_createTime < %s" % (
                queryCIName, self.startTime, self.endTime)
            average_exec_time_all_commit = self.data_handler(
                average_exec_time_all_commit_query_stat)
            ci_index[ci]['exec_time_all_commit'] = average_exec_time_all_commit

            #所有commit等待时间
            average_wait_time_all_commit_query_stat = "select waitTime_total/60 as t from paddle_ci_status where %s and commit_createTime >= %s and commit_createTime < %s and waitTime_total>0 " % (
                queryCIName, self.startTime, self.endTime)
            average_wait_time_all_commit = self.data_handler(
                average_wait_time_all_commit_query_stat)
            ci_index[ci]['wait_time_all_commit'] = average_wait_time_all_commit

            #所有commit编译/单测时间
            for index in self.detailTimeIndex:
                index_all_commit_query_stat = "select %s/60 as t from paddle_ci_index where %s and createTime >= %s and createTime < %s" % (
                    index, queryCIName, self.startTime, self.endTime)
                index_all_commit = self.data_handler(
                    index_all_commit_query_stat)
                ci_index[ci]['%s_all_commit' % index] = index_all_commit

            #成功commit执行时间
            average_exec_time_success_commit_query_stat = "select execTime_total/60 as t from paddle_ci_status where %s and status='success' and documentfix='False' and commit_createTime >= %s and commit_createTime < %s" % (
                queryCIName, self.startTime, self.endTime)
            average_exec_time_success_commit = self.data_handler(
                average_exec_time_success_commit_query_stat)
            ci_index[ci][
                'exec_time_success_commit'] = average_exec_time_success_commit

            #成功commit等待时间
            average_wait_time_success_commit_query_stat = "select waitTime_total/60 as t from paddle_ci_status where %s and status='success' and commit_createTime >= %s and commit_createTime < %s and waitTime_total>0" % (
                queryCIName, self.startTime, self.endTime)
            average_wait_time_success_commit = self.data_handler(
                average_wait_time_success_commit_query_stat)
            ci_index[ci][
                'wait_time_success_commit'] = average_wait_time_success_commit

            #成功commit编译/单测时间
            for index in self.detailTimeIndex:
                index_success_commit_query_stat = "select %s/60 as t from paddle_ci_index where %s and EXCODE=0 and createTime >= %s and createTime < %s" % (
                    index, queryCIName, self.startTime, self.endTime)
                index_success_commit = self.data_handler(
                    index_success_commit_query_stat)
                ci_index[ci]['%s_success_commit' %
                             index] = index_success_commit

            #所有commit耗时/ 成功commit耗时:执行+排队 
            if None not in ci_index[ci]['wait_time_all_commit']:
                ci_index[ci]['consum_time_all_commit'] = [
                    round(
                        float(ci_index[ci]['wait_time_all_commit'][i] +
                              ci_index[ci]['exec_time_all_commit'][i]), 2)
                    for i in range(len(ci_index[ci]['exec_time_all_commit']))
                ]
            if None not in ci_index[ci]['wait_time_success_commit']:
                ci_index[ci]['consum_time_success_commit'] = [
                    round(
                        float(ci_index[ci]['wait_time_success_commit'][i] +
                              ci_index[ci]['exec_time_success_commit'][i]), 2)
                    for i in range(
                        len(ci_index[ci]['exec_time_success_commit']))
                ]

            aggregation_data = {}
            aggregation_data['ciName'] = ci
            aggregation_data['commit_createTime'] = self.startTime
            for key in ci_index[ci]:
                aggregation_data['%s_time_point_max' %
                                 key] = ci_index[ci][key][0]
                aggregation_data['%s_time_point_90' %
                                 key] = ci_index[ci][key][1]
                aggregation_data['%s_time_point_50' %
                                 key] = ci_index[ci][key][2]
                aggregation_data['%s_mean_time' % key] = ci_index[ci][key][3]

            result = self.db.insert('paddle_ci_aggregation_by_day',
                                    aggregation_data)

    def data_handler(self, queryStat):
        """
        return: [max_time, time_point_90, time_point_50, mean_time]
        """
        result = list(self.db.query(queryStat))
        if len(result) == 0:
            res = [None, None, None, None]
        else:
            time_list = []
            for task in result[0]:
                if task['t'] != None:
                    time_list.append(task['t'])
            time_list.sort(reverse=True)
            if len(time_list) == 0:
                return [None, None, None, None]
            if len(time_list) < 2:
                max_time = time_list[0]
            i = 0
            while i < len(time_list):
                if len(time_list) < 2:
                    max_time = time_list[0]
                    break
                if time_list[i] - time_list[i +
                                            1] > 120:  #最长的要比第二长的多等2h，就认为有异常
                    stat = 'select * from (' + queryStat.replace(
                        ' from',
                        ',* from') + ') where t=%s' % int(time_list[i])
                    res = list(self.db.query(stat))
                    res[0][0]['PR'] = str(res[0][0]['PR'])
                    del res[0][0]['t']
                    result = self.db.insert('paddle_ci_exception', res[0][0])
                    time_list.pop(i)
                else:
                    max_time = round(time_list[i], 2)
                    break
            time_point_50 = round(float(np.percentile(time_list, 50)), 2)
            time_point_90 = round(float(np.percentile(time_list, 90)), 2)
            mean_time = round(float(np.mean(time_list)), 2)
            res = [max_time, time_point_90, time_point_50, mean_time]
        return res


def getBetweenDay(begin_date, end_date=None):
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    if end_date == None:
        end_date = datetime.datetime.strptime(
            time.strftime('%Y-%m-%d', time.localtime(time.time())), "%Y-%m-%d")
    else:
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y-%m-%d")
        zeroToday = '%s 00:00:00' % date_str
        ciindex = ciIndex_dataAggregation(zeroToday)
        ciindex.time_EveryDayAggregation()
        begin_date += datetime.timedelta(days=1)
        time.sleep(1)


if __name__ == "__main__":
    today = datetime.date.today()
    queryTime = str(today + datetime.timedelta(days=-2))  #查询时间是两天前的
    getBetweenDay(queryTime, queryTime)  #这个时间是左闭右闭
