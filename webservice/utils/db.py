from influxdb import InfluxDBClient
import time

#INFLUXDB_IP = "180.76.162.151"
INFLUXDB_IP = "154.85.48.94"
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = "PaddleCI"

class Database(object):
    """Database"""
    def __init__(self):
        self._client = InfluxDBClient(host=INFLUXDB_IP, port=8086, username='Paddle_dev', password='baidu123', database=INFLUXDB_DATABASE)

    def insert(self, table, index_dict):
        data_points = [{"measurement": table, "fields":index_dict}]
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

    def queryDBlastHour(self, ci, repo, ifDocument):
        """过去2h成功的耗时"""
        endTime = int(time.time())
        startTime = endTime - 3600*2
        if ci == 'PR-CI-Mac':
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, startTime, endTime)
        elif ci == 'PR-CI-Windows':
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, startTime, endTime)
        else:
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, startTime, endTime)
        execTime_last1hour = self.queryDB(execTime_last1hour_query_stat, 'mean')
        if execTime_last1hour == None:
            lastday = endTime - 3600*24*7  #如果过去两小时没有成功的ci,就拿过去一周的数据
            if ci == 'PR-CI-Mac':
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, lastday, endTime)
            elif ci == 'PR-CI-Windows':
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, lastday, endTime)
            else:
                execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (ci, repo, ifDocument, lastday, endTime)
            execTime_last1hour = self.queryDB(execTime_last1hour_query_stat, 'mean')
        if execTime_last1hour != None and int(execTime_last1hour) == 0:
            execTime_last1hour = 2
        else:
            execTime_last1hour = int(execTime_last1hour) if execTime_last1hour != None else None
        return execTime_last1hour

