import sys
sys.path.append("..")
from utils.db import Database
from utils.common import CommonModule
from flask import Flask
from flask import request
import json


class ciIndexTrend():
    def __init__(self, ciName, startTime, endTime):
        self.db = Database()
        self.common = CommonModule()
        self.startTime = self.common.strTimeToTimestamp(startTime)
        self.endTime = self.common.strTimeToTimestamp(endTime)
        self.ciName = ciName
        self.errorEXCODE = {
            'NetWork Not Work': 503,
            'Build Failed': 7,
            'Test Failed': 8,
            'CoverageRatio Failed': 9,
            'Unknow Error': 1
        }

    def baseTime(self, queryEvent):
        """查询时间"""
        baseTime_dict = {
            'waitTime_total': '平均排队时间',
            'execTime_total': '平均执行时间'
        }
        query_string = '%s_max_time, %s_mean_time_10, %s_mean_time_30, %s_mean_time_50, %s_mean_time_70, %s_mean_time_90, %s_mean_time' % (
            queryEvent, queryEvent, queryEvent, queryEvent, queryEvent,
            queryEvent, queryEvent)
        query_stat = "SELECT %s,commit_createTime FROM paddle_ci_time_analysis where ciName='%s' and commit_createTime >= %s and commit_createTime <= %s ORDER BY time" % (
            query_string, self.ciName, self.startTime, self.endTime)
        result = list(self.db.query(query_stat))
        data = {}
        categories = []
        max_time_list = []
        mean_time_10_list = []
        mean_time_30_list = []
        mean_time_50_list = []
        mean_time_70_list = []
        mean_time_90_list = []
        mean_time_list = []
        data['series'] = []
        series = []
        series_data1 = {}
        series_data2 = {}
        series_data3 = {}
        series_data4 = {}
        series_data5 = {}
        series_data6 = {}
        series_data7 = {}
        for res in result[0]:
            localtime = self.common.TimestampTostrTime(res[
                'commit_createTime'])
            categories.append(localtime)
            max_time_list.append(res['%s_max_time' % queryEvent])
            mean_time_10_list.append(res['%s_mean_time_10' % queryEvent])
            mean_time_30_list.append(res['%s_mean_time_30' % queryEvent])
            mean_time_50_list.append(res['%s_mean_time_50' % queryEvent])
            mean_time_70_list.append(res['%s_mean_time_70' % queryEvent])
            mean_time_90_list.append(res['%s_mean_time_90' % queryEvent])
            mean_time_list.append(res['%s_mean_time' % queryEvent])
        series_data1['name'] = '耗时最长'
        series_data1['data'] = max_time_list
        series.append(series_data1)
        series_data2['name'] = '最长的前10%任务的平均耗时'
        series_data2['data'] = mean_time_10_list
        series.append(series_data2)
        series_data3['name'] = '最长的前30%任务的平均耗时'
        series_data3['data'] = mean_time_30_list
        series.append(series_data3)
        series_data4['name'] = '最长的前50%任务的平均耗时'
        series_data4['data'] = mean_time_50_list
        series.append(series_data4)
        series_data5['name'] = '最长的前70%任务的平均耗时'
        series_data5['data'] = mean_time_70_list
        series.append(series_data5)
        series_data6['name'] = '最长的前90%任务的平均耗时'
        series_data6['data'] = mean_time_90_list
        series.append(series_data6)
        series_data7['name'] = '平均耗时'
        series_data7['data'] = mean_time_list
        series.append(series_data7)
        data['categories'] = categories
        data['series'] = series
        res = {"status": 0, "msg": "", "data": data}
        return res

    def getLongestTime(self):
        max_time_list = []
        data = {}
        series = []
        consumetime_total_dict = {
            'longest_consumetime_total_max_time': [],
            'longest_consumetime_total_mean_time_10': [],
            'longest_consumetime_total_mean_time_30': [],
            'longest_consumetime_total_mean_time_50': [],
            'longest_consumetime_total_mean_time_70': [],
            'longest_consumetime_total_mean_time_90': [],
            'longest_consumetime_total_mean_time': []
        }
        consumetime_total_value_dict = {
            'longest_consumetime_total_max_time': '耗时最长',
            'longest_consumetime_total_mean_time_10': '最长的前10%任务的平均耗时',
            'longest_consumetime_total_mean_time_30': '最长的前30%任务的平均耗时',
            'longest_consumetime_total_mean_time_50': '最长的前50%任务的平均耗时',
            'longest_consumetime_total_mean_time_70': '最长的前70%任务的平均耗时',
            'longest_consumetime_total_mean_time_90': '最长的前90%任务的平均耗时',
            'longest_consumetime_total_mean_time': '平均耗时'
        }

        consumetime_total_list = [
            'consumetime_total_max_time', 'consumetime_total_mean_time_10',
            'consumetime_total_mean_time_30', 'consumetime_total_mean_time_50',
            'consumetime_total_mean_time_70', 'consumetime_total_mean_time_90',
            'consumetime_total_mean_time'
        ]
        for queryEvent in consumetime_total_list:
            categories = []
            queryEvent = 'longest_%s' % queryEvent
            query_stat = "SELECT %s,ciName,commit_createTime FROM paddle_ci_longest_time_table where commit_createTime >= %s and commit_createTime <= %s ORDER BY time" % (
                queryEvent, self.startTime, self.endTime)
            result = list(self.db.query(query_stat))
            for event in result[0]:
                if event[queryEvent] != None:
                    localtime = self.common.TimestampTostrTime(event[
                        'commit_createTime'])
                    categories.append(localtime)
                    consumetime_total_dict[queryEvent].append(event[
                        queryEvent])
        data['categories'] = categories
        for index in consumetime_total_dict:
            series_data = {}
            series_data['name'] = consumetime_total_value_dict[index]
            series_data['data'] = consumetime_total_dict[index]
            series.append(series_data)
        data['series'] = series
        res = {"status": 0, "msg": "", "data": data}
        return res

    def getLongestTimeTable(self):
        columns = [{
            "name": "时间",
            "id": "time"
        }, {
            "name": "",
            "id": "key"
        }, {
            "name": "ciName",
            "id": "ciName"
        }, {
            "name": "平均耗时",
            "id": "consume_time"
        }]
        row = []
        consumetime_total_list = ['consumetime_total_mean_time']
        query_stat = "SELECT longest_consumetime_total_mean_time,ciName,commit_createTime FROM paddle_ci_longest_time_table where commit_createTime >= %s and commit_createTime <= %s ORDER BY time" % (
            self.startTime, self.endTime)
        result = list(self.db.query(query_stat))
        for event in result[0]:
            if event[queryEvent] != None:
                localtime = self.common.TimestampTostrTime(event[
                    'commit_createTime'])
                categories.append(localtime)
                consumetime_total_dict[queryEvent].append(event[queryEvent])
        data['categories'] = categories
        for index in consumetime_total_dict:
            series_data = {}
            series_data['name'] = consumetime_total_value_dict[index]
            series_data['data'] = consumetime_total_dict[index]
            series.append(series_data)
        data['series'] = series
        res = {"status": 0, "msg": "", "data": data}
        return res


app = Flask(__name__)


@app.route('/ciindex_analysis', methods=['POST'])
def analysis_arguments():
    arguments = json.loads(request.data)
    for i in arguments['conditions']:
        if i['k'] == 'select':
            ciName = i['v']
        elif i['k'] == 'dateRange':
            dateRange = i['v']
            startTime = '%s 00:00:00' % dateRange.split(',')[0]
            endTime = '%s 00:00:00' % dateRange.split(',')[1]
    return ciName, startTime, endTime


@app.route('/ciindex_analysis/waittime', methods=['POST'])
def waittime_api():
    ciName, startTime, endTime = analysis_arguments()
    ciIndex_trend = ciIndexTrend(ciName, startTime, endTime)
    waitTime_data = ciIndex_trend.baseTime('waitTime_total')
    data = waitTime_data
    return data


@app.route('/ciindex_analysis/exectime', methods=['POST'])
def exectime_api():
    ciName, startTime, endTime = analysis_arguments()
    ciIndex_trend = ciIndexTrend(ciName, startTime, endTime)
    execTime_data = ciIndex_trend.baseTime('execTime_total')
    data = execTime_data
    return data


@app.route('/ciindex_analysis/consumetime', methods=['POST'])
def consumetime_api():
    ciName, startTime, endTime = analysis_arguments()
    ciIndex_trend = ciIndexTrend(ciName, startTime, endTime)
    consumeTime_data = ciIndex_trend.baseTime('consumetime_total')
    return consumeTime_data


@app.route('/ciindex_analysis/longesttime', methods=['POST'])
def longesttime_api():
    ciName, startTime, endTime = analysis_arguments()
    ciIndex_trend = ciIndexTrend(ciName, startTime, endTime)
    longesttime_data = ciIndex_trend.getLongestTime()
    data = longesttime_data
    return data


if __name__ == '__main__':
    app.run(host='xx:xx:xx:xx', port=8096)
