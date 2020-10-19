import json
import time
import sys
sys.path.append("..")
from utils.db import Database


def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count


def queryDBlastHour(ci, repo, ifDocument):
    """过去2h成功的耗时"""
    endTime = int(time.time())
    startTime = endTime - 3600 * 2
    if ci == 'PR-CI-Mac':
        execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, repo, ifDocument, startTime, endTime)
    elif ci == 'PR-CI-Windows':
        execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, repo, ifDocument, startTime, endTime)
    else:
        execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
            ci, repo, ifDocument, startTime, endTime)
    execTime_last1hour = queryDB(execTime_last1hour_query_stat, 'mean')
    if execTime_last1hour == None:
        lastday = endTime - 3600 * 24 * 7
        if ci == 'PR-CI-Mac':
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Mac-Python3/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, lastday, endTime)
        elif ci == 'PR-CI-Windows':
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and ciName !~ /^PR-CI-Windows-OPENBLAS/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, lastday, endTime)
        else:
            execTime_last1hour_query_stat = "SELECT mean(execTime_total)/60 from paddle_ci_status where ciName =~ /^%s/ and repo='%s' and documentfix='%s' and status='success' and paddle_build_endTime > %s and paddle_build_endTime < %s and time > '2020-07-09 07:40:00'" % (
                ci, repo, ifDocument, lastday, endTime)
        execTime_last1hour = queryDB(execTime_last1hour_query_stat, 'mean')
    if execTime_last1hour != None and int(execTime_last1hour) == 0:
        execTime_last1hour = 2
    else:
        execTime_last1hour = int(
            execTime_last1hour) if execTime_last1hour != None else None
    return execTime_last1hour


def getALLCIExecTime():
    """获取所有ci的执行时间"""
    """ciName_repo_ifDocument"""
    execTime_dict = {}
    with open("../conf/monitor.json", "r") as f:
        repo_ci_dict = json.load(f)
    for repo in repo_ci_dict:
        for ci in repo_ci_dict[repo]:
            if repo in ['PaddlePaddle/Paddle']:
                if ci == 'PR-CI-CPU-Py2':
                    for ifDocument in [True, False]:
                        key = '%s_%s_%s' % (ci, repo, ifDocument)
                        execTime_dict[key] = queryDBlastHour(ci, repo,
                                                             ifDocument)
                else:
                    key = '%s_%s_True' % (ci, repo)
                    execTime_dict[key] = 2
                    key = '%s_%s_False' % (ci, repo)
                    execTime_dict[key] = queryDBlastHour(ci, repo, 'False')
            else:
                ifDocument = False
                key = '%s_%s_%s' % (ci, repo, ifDocument)
                execTime_dict[key] = queryDBlastHour(ci, repo, ifDocument)
    if execTime_dict[
            'PR-CI-OP-Benchmark_PaddlePaddle/benchmark_False'] == None:
        execTime_dict['PR-CI-OP-Benchmark_PaddlePaddle/benchmark_False'] = 15
    execTime_dict['build-paddle_PaddlePaddle/Paddle_False'] = 15
    with open("../buildLog/all_ci_execTime.json", "w") as f:
        json.dump(execTime_dict, f)
        f.close()


getALLCIExecTime()
