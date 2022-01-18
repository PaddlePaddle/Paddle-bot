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
            'PR-CI-Coverage', 'PR-CI-Py3', 'PR-CI-Clone', 'PR-CI-Build',
            'PR-CE-Framework', 'PR-CI-OP-benchmark', 'PR-CI-Model-benchmark',
            'PR-CI-Static-Check', 'PR-CI-Inference', 'PR-CI-Mac-Python3',
            'PR-CI-APPROVAL', 'PR-CI-Windows', 'PR-CI-Windows-OPENBLAS',
            'PR-CI-Windows-Inference', 'PR-CI-musl', 'PR-CI-Kunlun',
            'PR-CI-ROCM-Compile', 'PR-CI-NPU', 'PR-CI-GpuPS', 'PR-CI-CINN'
        ]
        self.db = Database()
        self.common = CommonModule()
        self.baseTimeIndex = ['waitTime_total', 'execTime_total']
        self.detailTimeIndex = ['buildTime', 'testCaseTime_total']
        self.startTime = self.common.strTimeToTimestamp(queryTime)
        self.endTime = self.startTime + 86400

    def timeIndex_rawdata(self, ciName, queryEvent, table='paddle_ci_status'):
        if table == 'paddle_ci_status':
            query_stat = "SELECT %s FROM paddle_ci_status where ciName='%s' and commit_createTime >= %s and commit_createTime < %s" % (
                queryEvent, ciName, self.startTime, self.endTime)
        elif table == 'paddle_ci_index':
            query_stat = "SELECT %s FROM paddle_ci_index where ciName='%s' and createTime >= %s and createTime < %s" % (
                queryEvent, ciName, self.startTime, self.endTime)
        result = list(self.db.query(query_stat))
        if len(result) == 0:
            res = [None, None, None, None, None, None, None]
        else:
            time_list = []
            for task in result[0]:
                time_list.append(task[queryEvent] / 60)
            time_list.sort(reverse=True)
            max_time = round(time_list[0], 2)
            timeList = np.array(time_list[0:math.ceil(len(time_list) * 0.1)])
            mean_time_10 = round(float(np.mean(timeList)), 2)
            timeList = np.array(time_list[0:math.ceil(len(time_list) * 0.3)])
            mean_time_30 = round(float(np.mean(timeList)), 2)
            timeList = np.array(time_list[0:math.ceil(len(time_list) * 0.5)])
            mean_time_50 = round(float(np.mean(timeList)), 2)
            timeList = np.array(time_list[0:math.ceil(len(time_list) * 0.7)])
            mean_time_70 = round(float(np.mean(timeList)), 2)
            timeList = np.array(time_list[0:math.ceil(len(time_list) * 0.9)])
            mean_time_90 = round(float(np.mean(timeList)), 2)
            timeList = np.array(time_list)
            mean_time = round(float(np.mean(timeList)), 2)
            res = [
                max_time, mean_time_10, mean_time_30, mean_time_50,
                mean_time_70, mean_time_90, mean_time
            ]
        return res

    def dataAggregation(self):
        """聚合"""
        for ciName in self.required_ci_list:
            print(ciName)
            aggregation_data = {}
            aggregation_data['ciName'] = ciName
            aggregation_data['commit_createTime'] = self.startTime
            #基础时间指标: 排队时间/执行时间
            for ciindex in self.baseTimeIndex:
                res = self.timeIndex_rawdata(ciName, ciindex)
                max_time, mean_time_10, mean_time_30, mean_time_50, mean_time_70, mean_time_90, mean_time = res[
                    0], res[1], res[2], res[3], res[4], res[5], res[6]
                aggregation_data['%s_max_time' % ciindex] = max_time
                aggregation_data['%s_mean_time_10' % ciindex] = mean_time_10
                aggregation_data['%s_mean_time_30' % ciindex] = mean_time_30
                aggregation_data['%s_mean_time_50' % ciindex] = mean_time_50
                aggregation_data['%s_mean_time_70' % ciindex] = mean_time_70
                aggregation_data['%s_mean_time_90' % ciindex] = mean_time_90
                aggregation_data['%s_mean_time' % ciindex] = mean_time

            #耗时=等待+执行
            if aggregation_data['waitTime_total_mean_time'] == None:
                if aggregation_data['execTime_total_mean_time'] == None:
                    consumetime_total_max_time = None
                    consumetime_total_mean_time_10 = None
                    consumetime_total_mean_time_30 = None
                    consumetime_total_mean_time_50 = None
                    consumetime_total_mean_time_70 = None
                    consumetime_total_mean_time_90 = None
                    consumetime_total_mean_time = None
                else:
                    consumetime_total_max_time = round(
                        aggregation_data['execTime_total_max_time'], 2)
                    consumetime_total_mean_time_10 = round(
                        aggregation_data['execTime_total_mean_time_10'], 2)
                    consumetime_total_mean_time_30 = round(
                        aggregation_data['execTime_total_mean_time_30'], 2)
                    consumetime_total_mean_time_50 = round(
                        aggregation_data['execTime_total_mean_time_50'], 2)
                    consumetime_total_mean_time_70 = round(
                        aggregation_data['execTime_total_mean_time_70'], 2)
                    consumetime_total_mean_time_90 = round(
                        aggregation_data['execTime_total_mean_time_90'], 2)
                    consumetime_total_mean_time = round(
                        aggregation_data['execTime_total_mean_time'], 2)
            else:
                if aggregation_data['execTime_total_mean_time'] == None:
                    consumetime_total_max_time = round(
                        aggregation_data['waitTime_total_max_time'], 2)
                    consumetime_total_mean_time_10 = round(
                        aggregation_data['waitTime_total_mean_time_10'], 2)
                    consumetime_total_mean_time_30 = round(
                        aggregation_data['waitTime_total_mean_time_30'], 2)
                    consumetime_total_mean_time_50 = round(
                        aggregation_data['waitTime_total_mean_time_50'], 2)
                    consumetime_total_mean_time_70 = round(
                        aggregation_data['waitTime_total_mean_time_70'], 2)
                    consumetime_total_mean_time_90 = round(
                        aggregation_data['execTime_total_mean_time_90'], 2)
                    consumetime_total_mean_time = round(
                        aggregation_data['waitTime_total_mean_time'], 2)
                else:

                    consumetime_total_max_time = round(
                        aggregation_data['waitTime_total_max_time'] +
                        aggregation_data['execTime_total_max_time'], 2)
                    consumetime_total_mean_time_10 = round(
                        aggregation_data['waitTime_total_mean_time_10'] +
                        aggregation_data['execTime_total_mean_time_10'], 2)
                    consumetime_total_mean_time_30 = round(
                        aggregation_data['waitTime_total_mean_time_30'] +
                        aggregation_data['execTime_total_mean_time_30'], 2)
                    consumetime_total_mean_time_50 = round(
                        aggregation_data['waitTime_total_mean_time_50'] +
                        aggregation_data['execTime_total_mean_time_50'], 2)
                    consumetime_total_mean_time_70 = round(
                        aggregation_data['waitTime_total_mean_time_70'] +
                        aggregation_data['execTime_total_mean_time_70'], 2)
                    consumetime_total_mean_time_90 = round(
                        aggregation_data['waitTime_total_mean_time_90'] +
                        aggregation_data['execTime_total_mean_time_90'], 2)
                    consumetime_total_mean_time = round(
                        aggregation_data['waitTime_total_mean_time'] +
                        aggregation_data['execTime_total_mean_time'], 2)

            aggregation_data[
                'consumetime_total_max_time'] = consumetime_total_max_time
            aggregation_data[
                'consumetime_total_mean_time_10'] = consumetime_total_mean_time_10
            aggregation_data[
                'consumetime_total_mean_time_30'] = consumetime_total_mean_time_30
            aggregation_data[
                'consumetime_total_mean_time_50'] = consumetime_total_mean_time_50
            aggregation_data[
                'consumetime_total_mean_time_70'] = consumetime_total_mean_time_70
            aggregation_data[
                'consumetime_total_mean_time_90'] = consumetime_total_mean_time_90
            aggregation_data[
                'consumetime_total_mean_time'] = consumetime_total_mean_timn
            if None not in aggregation_data.values():
                result = self.db.insert('paddle_ci_time_analysis',
                                        aggregation_data)
                print(result)

    def getLongestTime(self):
        consumetime_total_list = [
            'consumetime_total_max_time', 'consumetime_total_mean_time_10',
            'consumetime_total_mean_time_30', 'consumetime_total_mean_time_50',
            'consumetime_total_mean_time_70', 'consumetime_total_mean_time_90',
            'consumetime_total_mean_time'
        ]
        for queryEvent in consumetime_total_list:
            result = {}
            result['commit_createTime'] = self.startTime
            query_stat = "SELECT TOP(%s, 1),ciName FROM paddle_ci_time_analysis where commit_createTime = %s" % (
                queryEvent, self.startTime)
            res = list(self.db.query(query_stat))
            if len(res) != 0:
                result['longest_%s' % queryEvent] = res[0][0]['top']
                result['ciName'] = res[0][0]['ciName']
                db_result = self.db.insert('paddle_ci_longest_time_table',
                                           result)


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
        ciindex.dataAggregation()
        ciindex.getLongestTime()
        begin_date += datetime.timedelta(days=1)
        time.sleep(3)


if __name__ == "__main__":
    getBetweenDay('2022-01-01', '2022-01-16')
