import requests
import datetime
from db import Database
import handler
from auth_ipipe import Get_ipipe_auth


class Routine_Daily(object):
    def getTodayTargetsBuildTime(self):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        url = 'https://paddle-docker-tar.bj.bcebos.com/paddle_targets_buildtime_record/%s-buildTime.txt' % yesterday
        filename = '%s-buildTime.txt' % yesterday
        try:
            r = requests.get(url)
        except Exception as e:
            print("Error: %s" % e)
        else:
            with open("../buildLog/%s" % filename, "wb") as f:
                f.write(r.content)
                f.close()

    def buildTimeinsertDB(self):
        xly_handler = handler.xlyHandler()
        ciName = 'PR-CI-Build-Daily'
        hisory_record = xly_handler.getCIhistoryRecord(ciName)
        basic_ci_index_dict = {}
        index = hisory_record.json()[0]
        lastday_ci_status = index['status']
        triggerId = index['id']
        stage_url = 'https://xly.bce.baidu.com/open-api/ipipe/agile/pipeline/v1/pipelineBuild/%s' % triggerId
        session, req = Get_ipipe_auth(stage_url)
        try:
            res = session.send(req).json()
        except Exception as e:
            print("Error: %s" % e)
        else:
            basic_ci_index_dict['branch'] = res['branch']
            basic_ci_index_dict['ciName'] = 'PR-CI-Build-Daily'
            PR = res['pipelineBuildBean']['stageBuildBeans'][0]['outParams'][
                'AGILE_PULL_ID']
            basic_ci_index_dict['PR'] = PR
            basic_ci_index_dict['commitId'] = res['revision']
            basic_ci_index_dict['documentfix'] = 'False'
            basic_ci_index_dict['isRebuild'] = 0
            basic_ci_index_dict['repo'] = 'PaddlePaddle/Paddle'
            basic_ci_index_dict[
                'status'] = 'success' if lastday_ci_status == 'SUCC' else 'failure'
            basic_ci_index_dict[
                'EXCODE'] = 0 if lastday_ci_status == 'SUCC' else 1
            basic_ci_index_dict['triggerUser'] = 'dailyJob'
            commit_createTime = int(
                str(res['pipelineBuildBean']['startTime'])[:-3])  #任务触发时间
            commit_submitTime = int(
                str(res['buildInfoBean']['commitTime'])[:-3])
            basic_ci_index_dict['commit_createTime'] = commit_createTime
            basic_ci_index_dict['commit_submitTime'] = commit_submitTime
            stageBuildBean = res['pipelineBuildBean']['stageBuildBeans'][0]
            jobGroupBuildBeans = stageBuildBean['jobGroupBuildBeans']
            for Beans in jobGroupBuildBeans:
                for job in Beans:
                    if job['jobName'] == 'build-docker-image':
                        basic_ci_index_dict['docker_build_startTime'] = int(
                            str(job['startTime'])[:-3])
                        basic_ci_index_dict['docker_build_endTime'] = int(
                            str(job['endTime'])[:-3])
                    elif job['jobName'] == 'paddle-build':
                        basic_ci_index_dict['paddle_build_startTime'] = int(
                            str(job['startTime'])[:-3])
                        basic_ci_index_dict['paddle_build_endTime'] = int(
                            str(job['endTime'])[:-3])
                        logUrl = 'https://xly.bce.baidu.com/paddlepaddle/paddle/ibuild/auth/v2/xiaolvyun/log/downloadLog?%s' % job[
                            'realJobBuild']['logUrl']

            basic_ci_index_dict['waitTime_total'] = basic_ci_index_dict[
                'paddle_build_startTime'] - basic_ci_index_dict[
                    'docker_build_endTime']
            basic_ci_index_dict['execTime_total'] = (
                basic_ci_index_dict['paddle_build_endTime'] -
                basic_ci_index_dict['paddle_build_startTime']) + (
                    basic_ci_index_dict['docker_build_endTime'] -
                    basic_ci_index_dict['docker_build_startTime'])
            db = Database()
            result = db.insert('paddle_ci_status', basic_ci_index_dict)
            r = requests.get(logUrl)
            filename = "../buildLog/PR-CI-Build-Daily_%s_%s.log" % (
                basic_ci_index_dict['commitId'], commit_createTime)
            with open(filename, "wb") as f:
                f.write(r.content)
                f.close()

            detailed_ci_index_dict = {}

            detailed_ci_index_dict['ciName'] = basic_ci_index_dict['ciName']
            detailed_ci_index_dict['commitId'] = basic_ci_index_dict[
                'commitId']
            detailed_ci_index_dict['PR'] = int(basic_ci_index_dict['PR'])
            detailed_ci_index_dict['EXCODE'] = basic_ci_index_dict['EXCODE']
            detailed_ci_index_dict['triggerUser'] = basic_ci_index_dict[
                'triggerUser']
            detailed_ci_index_dict['createTime'] = basic_ci_index_dict[
                'commit_createTime']
            detailed_ci_index_dict['commit_submitTime'] = basic_ci_index_dict[
                'commit_submitTime']
            detailed_ci_index_dict['branch'] = basic_ci_index_dict['branch']
            detailed_ci_index_dict['repo'] = basic_ci_index_dict['repo']
            detailed_ci_index_dict['execTime_total'] = basic_ci_index_dict[
                'execTime_total']
            detailed_ci_index_dict['waitTime_total'] = basic_ci_index_dict[
                'waitTime_total']
            detailed_ci_index_dict['documentfix'] = basic_ci_index_dict[
                'documentfix']
            detailed_ci_index_dict['isRebuild'] = basic_ci_index_dict[
                'isRebuild']
            f = open(filename, 'r')
            data = f.read()
            buildTime_strlist = data.split('Build Time:', 1)
            buildTime = buildTime_strlist[1:][0].split('s')[0].strip()
            detailed_ci_index_dict['buildTime'] = float(buildTime)

            buildSize_strlist = data.split('Build Size:', 1)
            buildSize = buildSize_strlist[1:][0].split('G')[0].strip()
            detailed_ci_index_dict['buildSize'] = float(buildSize)

            WhlSize_strlist = data.split('PR whl Size:', 1)
            WhlSize = WhlSize_strlist[1:][0].split('M')[0].strip()
            detailed_ci_index_dict['WhlSize'] = float(WhlSize)

            ccacheRate_strlist = data.split('ccache hit rate:', 1)
            ccacheRate = ccacheRate_strlist[1:][0].split('%')[0].strip()
            detailed_ci_index_dict['ccacheRate'] = float(ccacheRate)

            result = db.insert('paddle_ci_index', detailed_ci_index_dict)
