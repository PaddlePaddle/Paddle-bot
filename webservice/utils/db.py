from influxdb import InfluxDBClient
import time
import os

INFLUXDB_IP = os.getenv("INFLUXDB_IP")
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = os.getenv("INFLUXDB_DATABASE")


class Database(object):
    """Database"""

    def __init__(self):
        self._client = InfluxDBClient(
            host=INFLUXDB_IP,
            port=8086,
            username='xxx',
            password='xxx',
            database=INFLUXDB_DATABASE)

    def insert(self, table, index_dict):
        data_points = [{"measurement": table, "fields": index_dict}]
        result = self._client.write_points(data_points)
        return result

    def query(self, query_stat):
        result = self._client.query(query_stat)
        return result

    def queryDB(self, query_stat, mode):
        result = list(self.query(query_stat))
        if len(result) == 0:
            count = None
        else:
            count = result[0][0][mode]
        return count

    def queryDBlastHour1(self, ci, repo, ifDocument):
        """过去2h成功的耗时"""
        endTime = int(time.time())
        startTime = endTime - 3600 * 2
        if ci.startswith('PR-CI-Mac'):
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, startTime, endTime)
        elif ci == 'PR-CI-Windows':
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, startTime, endTime)
        else:
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, startTime, endTime)
        execTime_last1hour = self.queryDB(execTime_last1hour_query_stat,
                                          'mean')
        if execTime_last1hour == None:
            lastday = endTime - 3600 * 24 * 7  #如果过去两小时没有成功的ci,就拿过去一周的数据
            if ci == 'PR-CI-Mac':
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                    ci, repo, ifDocument, lastday, endTime)
            elif ci == 'PR-CI-Windows':
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                    ci, repo, ifDocument, lastday, endTime)
            else:
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s'  and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                    ci, repo, ifDocument, lastday, endTime)
            execTime_last1hour = self.queryDB(execTime_last1hour_query_stat,
                                              'mean')
        if execTime_last1hour != None and int(execTime_last1hour) == 0:
            execTime_last1hour = 2
        else:
            execTime_last1hour = int(
                execTime_last1hour) if execTime_last1hour != None else None
        return execTime_last1hour

    def queryDBlastHour(self, ci, repo, queryType):
        """过去1天的成功耗时"""
        endTime = int(time.time())
        startTime = endTime - 3600 * 24
        if queryType == 'paddle-build':
            execTime_last1hour_query_stat = "SELECT mean(t)/60 from (SELECT paddle_build_endTime-paddle_build_startTime as t from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='False' and status='success' and commit_createTime > %s and commit_createTime < %s) " % (
                ci, repo, startTime, endTime)
        elif queryType == 'paddle-test':
            execTime_last1hour_query_stat = "SELECT mean(t)/60 from (SELECT paddle_test_endTime-paddle_test_startTime as t from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='False' and status='success' and commit_createTime > %s and commit_createTime < %s) " % (
                ci, repo, startTime, endTime)
        elif queryType == 'sa':
            if ci == 'PR-CI-Windows':
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and ciName !~ /^PR-CI-Windows-Inference/ and repo='%s' and documentfix='False' and status='success' and commit_createTime > %s and commit_createTime < %s" % (
                    ci, repo, startTime, endTime)
            else:
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='False' and status='success' and commit_createTime > %s and commit_createTime < %s " % (
                    ci, repo, startTime, endTime)
        if repo != 'PaddlePaddle/Paddle':
            startTime = endTime - 3600 * 24 * 7
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='False' and status='success' and commit_createTime > %s and commit_createTime < %s " % (
                ci, repo, startTime, endTime)
        if self.queryDB(execTime_last1hour_query_stat, 'mean') == None:

            execTime_last1hour = 40
        else:
            execTime_last1hour = round(
                float(self.queryDB(execTime_last1hour_query_stat, 'mean')), 2)

        return execTime_last1hour
