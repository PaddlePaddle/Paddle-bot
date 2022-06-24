import sys
sys.path.append("..")
from utils.db import Database
from utils.common import CommonModule
from flask import Flask
from flask import request
import json
import datetime
import os

db = Database()


@app.route('/ciindex_trend/targetsbuildtime', methods=['POST'])
def targetsbuildtime_api():
    arguments = json.loads(request.data)
    queryText = ''
    for index in arguments['conditions']:
        if index['k'] == 'date':
            queryTime = index['v']
        elif index['k'] == 'text':
            queryText = index['v']
        elif index['k'] == 'select':
            queryCI = index['v']

    queryTime_targets_dic = {}

    queryTime_tmp = datetime.datetime.strptime(queryTime, "%Y-%m-%d").date()
    currentTime = datetime.datetime.strptime(queryTime, "%Y-%m-%d").date()

    for i in range(30):
        if queryCI == 'PR-CI-Build-Daily':
            filename = '/home/zhangchunle/Paddle-bot/webservice/buildLog/%s-buildTime.txt' % currentTime
        elif queryCI == 'PR-CI-Coverage-Daily':
            filename = '/home/zhangchunle/Paddle-bot/webservice/buildLog/%s-coverage-buildTime.txt' % currentTime
        if not os.path.exists(filename):
            currentTime -= datetime.timedelta(days=1)
            if len(queryTime_targets_dic) == 20:
                break
            continue
        f = open(filename)
        lines = f.readlines()
        base_dic = {}
        for line in lines:
            if queryText != '':
                if 'The specified key does not exist' in line:
                    break
                if queryText in line:
                    line = line.strip().split(',')
                    filename = line[0].strip()
                    buildTime = line[1].strip()
                    base_dic[filename] = buildTime
            else:
                if 'The specified key does not exist' in line:
                    break
                line = line.strip().split(',')
                filename = line[0].strip()
                buildTime = line[1].strip()
                base_dic[filename] = buildTime

        if len(base_dic) != 0:
            if i < 10:
                queryTime_targets_dic['0%s_%s' %
                                      (i, str(currentTime))] = base_dic
            else:
                queryTime_targets_dic['%s_%s' %
                                      (i, str(currentTime))] = base_dic
        currentTime -= datetime.timedelta(days=1)
        if len(queryTime_targets_dic) == 20:
            break

    queryTime_list = sorted(queryTime_targets_dic)
    columns = [{'name': '编译产出', 'id': 'filename'}]
    for i in range(len(queryTime_list)):
        column = {}
        t = queryTime_list[i].split('_')[1]
        column['name'] = '%s 编译时间/秒' % t
        column['id'] = 'buildTime_%s' % i
        columns.append(column)
    rows = []
    for filename in queryTime_targets_dic[queryTime_list[0]]:
        row = {}
        row['filename'] = filename
        row['buildTime_0'] = queryTime_targets_dic[queryTime_list[0]][filename]
        for i in range(1, len(queryTime_list)):
            if filename in queryTime_targets_dic[queryTime_list[i]]:
                row['buildTime_%s' %
                    i] = queryTime_targets_dic[queryTime_list[i]][filename]
            else:
                row['buildTime_%s' % i] = '-'

        rows.append(row)
    data = {"columns": columns, "rows": rows}
    res = {
        "status": 0,
        #"hitSugarSelf": true,
        "msg": "",
        "data": data
    }
    return res


@app.route('/ciindex_trend/allbuildtime', methods=['POST'])
def allbuildtime_api():
    arguments = json.loads(request.data)
    queryText = ''
    for index in arguments['conditions']:
        if index['k'] == 'date':
            queryTime = index['v']
        elif index['k'] == 'text':
            queryText = index['v']
        elif index['k'] == 'select':
            queryCI = index['v']

    queryTime_dic = {}

    queryTime_tmp = datetime.datetime.strptime(queryTime, "%Y-%m-%d").date()
    currentTime = datetime.datetime.strptime(queryTime, "%Y-%m-%d").date()

    queryTime_buildTime_dic = {}
    before30Day = currentTime - datetime.timedelta(days=30)
    NextDay = currentTime + datetime.timedelta(days=1)
    if queryCI == 'PR-CI-Build-Daily':
        query_stat = "select buildTime/60 from paddle_ci_index where ciName='PR-CI-Build-Daily' and time > '%s' and  time < '%s' order by time desc" % (
            before30Day, NextDay)
    elif queryCI == 'PR-CI-Coverage-Daily':
        query_stat = "select buildTime/60 from paddle_ci_index where ciName='PR-CI-Coverage-compile-Daily' and time > '%s' and  time < '%s' order by time desc" % (
            before30Day, NextDay)
    result = list(db.query(query_stat))
    for index in result[0]:
        t = index['time'].split('T')[0]
        buildTime = round(float(index['buildTime']), 2)
        queryTime_buildTime_dic[t] = buildTime
        if len(queryTime_buildTime_dic) == 20:
            break
    columns = [{'name': '', 'id': 'queryTime'}]
    rows = {'queryTime': '编译时间/min'}
    for queryTime in queryTime_buildTime_dic:
        column = {}
        column['name'] = queryTime
        column['id'] = 'buildTime_%s' % queryTime
        rows['buildTime_%s' % queryTime] = queryTime_buildTime_dic[queryTime]
        columns.append(column)

    data = {"columns": columns, "rows": [rows]}

    res = {
        "status": 0,
        #"hitSugarSelf": true,
        "msg": "",
        "data": data
    }
    return res


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8098)
