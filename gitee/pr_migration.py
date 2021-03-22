import requests
import os
import json
import logging
import time
import datetime
from handler import GiteePROperation
from pr_merge import gitee_merge_pr

logging.basicConfig(
    level=logging.INFO,
    filename='./logs/pr.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
"""Github PR Migrate to Gitee"""


class GithubRepo(object):
    def __init__(self):
        self.commitUrl = 'https://api.github.com/repos/{owner}/{repo}/commits'
        self.prUrl = 'https://api.github.com/repos/{owner}/{repo}/pulls'
        self.headers = {'authorization': "token xxx"}

    def utcTimeToStrTime(self, utcTime):
        """utc时间转换为当地时间"""
        UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        utcTime = datetime.datetime.strptime(utcTime, UTC_FORMAT)
        localtime = utcTime + datetime.timedelta(hours=8)
        return localtime

    def getCommitList(self, commitId, beforeTime):
        """get github paddle repo commitidList after gitee lastest commitid"""
        commitUrl = self.commitUrl.format(owner='PaddlePaddle', repo='Paddle')
        ifContinue = True
        CommitList = []
        while (commitUrl != None):
            response = requests.get(commitUrl, headers=self.headers)
            for task in response.json():
                date = task['commit']['author']['date']
                localtime = self.utcTimeToStrTime(date)
                if localtime < beforeTime:  #获取某个时间段的commitid
                    if task['sha'] == commitId:
                        ifContinue = False
                        break
                    else:
                        CommitList.append(task['sha'])
            if ifContinue == True:
                commitUrl = response.links['next']['url']
            else:
                commitUrl = None
        return CommitList

    def getPRtitleAndBody(self, PR):
        """get PR's branch, title and body"""
        PRUrl = '%s/%s' % (self.prUrl.format(
            owner='PaddlePaddle', repo='Paddle'), PR)
        response = requests.get(PRUrl, headers=self.headers)
        response = json.loads(response.text)
        branch = response['head']['ref']
        title = response['title']
        body = response['body']

        return branch, title, body

    def getPRchangeFiles(self, commitId):
        """git PR change files List And PR"""
        commitUrl = '%s/%s' % (self.commitUrl.format(
            owner='PaddlePaddle', repo='Paddle'), commitId)
        response = requests.get(commitUrl, headers=self.headers).json()
        changeFiles = [f['filename'] for f in response['files']]
        PR = int(response['commit']['message'].split('#')[1].split(')')[0])
        return changeFiles, PR


class giteeRepo():
    def __init__(self):
        self.prUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/pulls'
        self.commitUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/commits'
        self.giteePaddlePath = 'Paddle-bot/gitee/gitee_Paddle'
        self.githubPaddlePath = 'Paddle-bot/gitee/Paddle'
        self.headers = {
            'authorization': 'token 04388373ac19b581f4d2e8238131b20a'
        }
        self.operation = GiteePROperation()

    def getlastestPR(self):
        """get lastest commitId in gitee Paddle repo"""
        prUrl = self.prUrl.format(
            owner='paddlepaddle', repo='Paddle') + '?state=merged'
        response = requests.get(prUrl)
        lastestPR = response.json()[0]['number']
        return lastestPR

    def prepareGiteeFiles(self, commitid, branch, title, changeFiles):
        for filename in changeFiles:
            os.system('cp -r %s/%s %s/%s' % (self.githubPaddlePath, filename,
                                             self.giteePaddlePath, filename))

    def create_pr(self, branch, title, body):
        """
        create a pr
        return PR, commitId
        """
        prUrl = self.prUrl.format(owner='paddlepaddle', repo='Paddle')
        payload = {
            "access_token": "04388373ac19b581f4d2e8238131b20a",
            "title": "%s" % title,
            "head": "PaddlePaddle-Gardener:%s" % branch,
            "base": "develop",
            "body": body
        }
        response = requests.request(
            "POST",
            prUrl,
            params=payload,
            headers={'Content-Type': 'application/json'})
        if response.status_code in [200, 201]:
            PR = response.json()['number']
            sha = response.json()['head']['sha']
            logger.info('Gitee PaddlePaddle/Paddle %s %s create success!' %
                        (PR, sha))
            return PR, sha
        else:
            logger.error('Gitee PaddlePaddle/Paddle %s %s create failed!' %
                         (PR, sha))
            return None, None


class githubPrMigrateGitee():
    def __init__(self):
        self.giteePaddle = giteeRepo()
        self.githubPaddle = GithubRepo()

    def tranGiteeCommittoGithubCommit(self):
        """
        gitee的commitid与GitHub的不一致
        """
        with open('/home/zhangchunle/Paddle-bot/gitee/commitmap.json',
                  'r') as f:
            data = json.load(f)
            f.close()
        return data

    def ifPRconflict(self, changeFiles):
        """
        当天提交的PR是否可能有PR冲突
        """
        ifconflict = False
        with open('/home/zhangchunle/Paddle-bot/gitee/commitmap.json',
                  'r') as f:
            data = json.load(f)
            f.close()
        for key in data:
            for filename in changeFiles:
                if filename in data[key]['changeFiles']:
                    ifconflict = True
                    break
            if ifconflict == True:
                break
        return ifconflict

    def main(self):
        os.system('bash update_code.sh giteePaddle')
        os.system('bash update_code.sh githubPaddle')
        now = datetime.datetime.now()
        beforeTime = now - datetime.timedelta(
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond)
        lastestPR_gitee = self.giteePaddle.getlastestPR()
        commitmap = self.tranGiteeCommittoGithubCommit()
        commitId_github = commitmap['%s' % lastestPR_gitee]['githubCommitId']
        CommitList_github = self.githubPaddle.getCommitList(commitId_github,
                                                            beforeTime)
        commit_map = {}
        for commitId in CommitList_github[::-1]:
            commit_map_value = {}
            changeFiles, PR = self.githubPaddle.getPRchangeFiles(commitId)
            ifconflict = self.ifPRconflict(changeFiles)
            if ifconflict == True:
                gitee_merge_pr()
                time.sleep(10)
                os.system('bash update_code.sh giteePaddle')  # merge后要更新环境
                commit_map = {}
            commit_map_value['changeFiles'] = changeFiles
            commit_map_value['githubCommitId'] = commitId
            branch, title, body = self.githubPaddle.getPRtitleAndBody(PR)
            os.system('bash update_code.sh migrateEnv %s %s' %
                      (commitId, branch))
            self.giteePaddle.prepareGiteeFiles(commitId, branch, title,
                                               changeFiles)
            os.system('bash update_code.sh prepareCode %s %s %s' %
                      (commitId, branch, title))
            PR, sha = self.giteePaddle.create_pr(branch, title, body)
            commit_map_value['sha'] = sha
            commit_map[PR] = commit_map_value
            with open('commitmap.json', 'w') as f:
                json.dump(commit_map, f)
                f.close()


githubPrMigrateGitee().main()
