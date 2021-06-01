import requests
import os
import json
import logging
import time
import datetime
from gitee.handler import GiteePROperation
from gitee.pr_merge import gitee_merge_pr, sendMail

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
        self.headers = {'authorization': "token xxxxxxx"}

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
        changeFiles_dict = {}
        changeFiles_dict['modified'] = []
        changeFiles_dict['removed'] = []
        changeFiles_dict['added'] = []
        changeFiles_dict['renamed'] = []
        for f in response['files']:
            if f['status'] == 'modified':
                changeFiles_dict['modified'].append(f['filename'])
            elif f['status'] == 'removed':
                changeFiles_dict['removed'].append(f['filename'])
            elif f['status'] == 'added':
                changeFiles_dict['added'].append(f['filename'])
            elif f['status'] == 'renamed':
                renamed_file = '%s:%s' % (f['previous_filename'],
                                          f['filename'])  #old_name:new_name
                changeFiles_dict['renamed'].append(renamed_file)
        search_pr_url = 'https://api.github.com/search/issues?q=sha:%s+is:merged+is:pr+repo:PaddlePaddle/Paddle' % commitId
        res = requests.get(search_pr_url, headers=self.headers).json()
        PR = res['items'][0]['number']
        return changeFiles_dict, PR


class giteeRepo():
    def __init__(self):
        self.prUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/pulls'
        self.commitUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/commits'
        self.giteePaddlePath = '/home/zhangchunle/Paddle-bot/gitee/gitee_Paddle'
        self.githubPaddlePath = '/home/zhangchunle/Paddle-bot/gitee/Paddle'
        self.headers = {'authorization': 'token xxxxx'}
        self.operation = GiteePROperation()

    def getlastestPR(self):
        """get lastest PR in gitee Paddle repo"""
        prUrl = self.prUrl.format(
            owner='paddlepaddle', repo='Paddle') + '?state=merged'
        response = requests.get(prUrl)
        lastestPR = response.json()[0]['number']

        return lastestPR

    def getlastestCommit(self):
        """get lastest commitId in gitee Paddle repo"""
        commitUrl = self.commitUrl.format(owner='paddlepaddle', repo='Paddle')
        response = requests.get(commitUrl)
        lastestCommit = response.json()[0]['sha']
        return lastestCommit

    def prepareGiteeFiles(self, commitid, branch, title, changeFiles):
        for file_type in changeFiles:
            if file_type == 'added':
                for filename in changeFiles[file_type]:
                    giteePaddlePath = self.giteePaddlePath + '/' + filename.replace(
                        filename.split('/')[-1], '')
                    os.system('mkdir -p %s' % giteePaddlePath)
                    os.system('touch %s/%s' % (self.giteePaddlePath, filename))
                    os.system('cp -r %s/%s %s/%s' %
                              (self.githubPaddlePath, filename,
                               self.giteePaddlePath, filename))
            elif file_type == 'modified':
                for filename in changeFiles[file_type]:
                    os.system('cp -r %s/%s %s/%s' %
                              (self.githubPaddlePath, filename,
                               self.giteePaddlePath, filename))
            elif file_type == 'removed':
                for filename in changeFiles[file_type]:
                    os.system('rm -rf %s/%s' %
                              (self.giteePaddlePath, filename))
            elif file_type == 'renamed':
                for filename in changeFiles[file_type]:
                    old_name = filename.split(':')[0]
                    new_name = filename.split(':')[1]
                    os.system('mv %s/%s %s/%s' %
                              (self.giteePaddlePath, old_name,
                               self.giteePaddlePath, new_name))

    def create_pr(self, branch, title, body):
        """
        create a pr
        return PR, commitId
        """
        prUrl = self.prUrl.format(owner='paddlepaddle', repo='Paddle')
        payload = {"access_token": "xxxx"}
        data = {
            "title": "%s" % title,
            "head": "PaddlePaddle-Gardener:%s" % branch,
            "base": "develop",
            "body": body
        }
        response = requests.request(
            "POST",
            prUrl,
            params=payload,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'})
        if response.status_code == 400 and '不存在差异' in response.json()[
                'message']:
            return None, None
        else:
            count = 0
            while response.status_code not in [200, 201]:
                time.sleep(10)
                response = requests.request(
                    "POST",
                    prUrl,
                    params=payload,
                    headers={'Content-Type': 'application/json'})
                count += 1
                if count >= 3:
                    break
            if response.status_code in [200, 201]:
                PR = response.json()['number']
                sha = response.json()['head']['sha']
                logger.info('Gitee PaddlePaddle/Paddle %s %s create success!' %
                            (PR, sha))
                return PR, sha
            else:
                title = '[告警]Gitee提交PR失败'
                receivers = ['zhangchunle@baidu.com']
                mail_content = 'PR: %s, data: %s, %s' % (prUrl, data,
                                                         response.text)
                sendMail(title, mail_content, receivers)
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
        changeFiles_list = []
        for file_type in changeFiles:
            if file_type == 'renamed':
                for filename in changeFiles[file_type]:
                    changeFiles_list.append(filename.split(':')[0])
                    changeFiles_list.append(filename.split(':')[1])
            else:
                for filename in changeFiles[file_type]:
                    changeFiles_list.append(filename)
        for key in data:
            for filename in changeFiles_list:
                if filename in data[key]['changeFiles']:
                    ifconflict = True
                    break
            if ifconflict == True:
                break
        return ifconflict

    def main(self):
        os.system(
            'bash /home/zhangchunle/Paddle-bot/gitee/update_code.sh giteePaddle'
        )
        os.system(
            'bash /home/zhangchunle/Paddle-bot/gitee/update_code.sh githubPaddle'
        )

        now = datetime.datetime.now()
        beforeTime = now - datetime.timedelta(
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond)
        print(beforeTime)

        #lastestCommit_gitee = self.giteePaddle.getlastestCommit()
        #print(lastestCommit_gitee)
        #CommitList_github = self.githubPaddle.getCommitList(lastestCommit_gitee, beforeTime)
        #print(CommitList_github)

        lastestPR_gitee = self.giteePaddle.getlastestPR()

        commitmap = self.tranGiteeCommittoGithubCommit()
        commitId_github = commitmap['%s' % lastestPR_gitee]['githubCommitId']
        CommitList_github = self.githubPaddle.getCommitList(commitId_github,
                                                            beforeTime)
        commit_map = {}
        with open('/home/zhangchunle/Paddle-bot/gitee/commitmap.json',
                  'w') as f:  #清空commit map
            json.dump(commit_map, f)
            f.close()
        for commitId in CommitList_github[::-1]:
            print(commitId)
            commit_map_value = {}
            changeFiles, PR = self.githubPaddle.getPRchangeFiles(commitId)
            ifconflict = self.ifPRconflict(changeFiles)
            if ifconflict == True:
                gitee_merge_pr()
                time.sleep(10)
                os.system(
                    'bash /home/zhangchunle/Paddle-bot/gitee/update_code.sh giteePaddle'
                )  # merge后要更新环境
                commit_map = {}
            commit_map_value['changeFiles'] = changeFiles
            commit_map_value['githubCommitId'] = commitId
            branch, title, body = self.githubPaddle.getPRtitleAndBody(PR)
            if branch == 'develop':
                branch = 'dev_pr_%s' % int(time.time())
            branch = branch.replace('/', '_')
            os.system(
                'bash /home/zhangchunle/Paddle-bot/gitee/update_code.sh migrateEnv %s %s'
                % (commitId, branch))
            self.giteePaddle.prepareGiteeFiles(commitId, branch, title,
                                               changeFiles)

            os.system(
                'bash /home/zhangchunle/Paddle-bot/gitee/update_code.sh prepareCode %s %s mirgate_%s'
                % (commitId, branch, PR))
            PR, sha = self.giteePaddle.create_pr(branch, title, body)
            if PR == None:
                break
            else:
                commit_map_value['sha'] = sha
                commit_map[PR] = commit_map_value
                with open('/home/zhangchunle/Paddle-bot/gitee/commitmap.json',
                          'w') as f:
                    json.dump(commit_map, f)
                    f.close()
            time.sleep(2)


githubPrMigrateGitee().main()
