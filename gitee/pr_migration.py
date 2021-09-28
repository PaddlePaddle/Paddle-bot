import requests
import os
import json
import logging
import time
import datetime
from gitee.handler import GiteePROperation
from gitee.pr_merge import gitee_merge_pr, sendMail

logging.basicConfig(level=logging.INFO, filename='./logs/pr.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

"""Github PR Migrate to Gitee"""

class GithubRepo(object):
    def __init__(self):
        self.commitUrl = 'https://api.github.com/repos/{owner}/{repo}/commits'
        self.prUrl = 'https://api.github.com/repos/{owner}/{repo}/pulls'
        self.headers = {'authorization': "token xxxx"}
    
    def utcTimeToStrTime(self, utcTime):
        """utc时间转换为当地时间"""
        UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        utcTime = datetime.datetime.strptime(utcTime, UTC_FORMAT)
        localtime = utcTime + datetime.timedelta(hours=8)
        return localtime

    def getCommitList(self, repo, commitId, beforeTime):
        """get github paddle repo commitidList after gitee lastest commitid"""
        commitUrl = self.commitUrl.format(owner='PaddlePaddle', repo=repo) + '?sha=develop'
        ifContinue = True
        CommitList = []
        while (commitUrl != None):
            response = requests.get(commitUrl, headers=self.headers)
            for task in response.json():
                date = task['commit']['author']['date']
                localtime = self.utcTimeToStrTime(date)
                if localtime < beforeTime: #获取某个时间段的commitid
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

    def getPRtitleAndBody(self, repo, PR):
        """get PR's branch, title and body"""
        PRUrl = '%s/%s' %(self.prUrl.format(owner='PaddlePaddle', repo=repo), PR)
        response = requests.get(PRUrl, headers=self.headers)
        response = json.loads(response.text)
        branch = response['head']['ref']
        title = response['title']
        body = response['body']
        return branch, title, body


    def getPRchangeFiles(self, repo, commitId):
        """git PR change files List And PR"""
        commitUrl = '%s/%s' %(self.commitUrl.format(owner='PaddlePaddle', repo=repo), commitId)
        response = requests.get(commitUrl, headers=self.headers).json()
        changeFiles_dict = {}
        changeFiles_dict['modified'] = []
        changeFiles_dict['removed'] = []
        changeFiles_dict['added'] = []
        changeFiles_dict['renamed'] = [] #
        for f in response['files']:
            if f['status'] == 'modified':
                changeFiles_dict['modified'].append(f['filename'])
            elif f['status'] == 'removed':
                changeFiles_dict['removed'].append(f['filename'])
            elif f['status'] == 'added':
                changeFiles_dict['added'].append(f['filename'])
            elif f['status'] == 'renamed':
                renamed_file = '%s:%s' %(f['previous_filename'], f['filename']) #old_name:new_name
                changeFiles_dict['renamed'].append(renamed_file)
        search_pr_url = 'https://api.github.com/search/issues?q=sha:%s+is:merged+is:pr+repo:PaddlePaddle/%s' %(commitId, repo)
        res = requests.get(search_pr_url, headers=self.headers).json()
        PR = res['items'][0]['number']
        return changeFiles_dict, PR

    def getPRMergeCommit(self, repo, PR):
        PRUrl = '%s/%s' %(self.prUrl.format(owner='PaddlePaddle', repo=repo), PR)
        response = requests.get(PRUrl, headers=self.headers).json()
        merge_commit_sha = response['merge_commit_sha']
        return merge_commit_sha

class giteeRepo():
    def __init__(self):
        self.prUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/pulls'
        self.commitUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/commits'
        self.giteePaddlePath = './Paddle-bot/gitee/gitee_{repo}'
        self.githubPaddlePath = './Paddle-bot/gitee/{repo}'
        self.headers = {'authorization': 'token xxx'}
        self.operation = GiteePROperation()

    def getlastestPR(self, repo):
        """get lastest PR in gitee Paddle repo"""
        prUrl = self.prUrl.format(owner='paddlepaddle', repo=repo) + '?state=merged'
        response = requests.get(prUrl)
        if len(response.text) == 0:
            return None
        lastestPR = response.json()[0]['number']
        return lastestPR

    def getlastestCommit(self, repo):
        """get lastest commitId in gitee Paddle repo"""
        commitUrl = self.commitUrl.format(owner='paddlepaddle', repo=repo)
        response = requests.get(commitUrl)
        lastestCommit = response.json()[0]['sha']
        return lastestCommit

    def getGithubPRInlastestPR(self, repo, PR):
        commitUrl = self.prUrl.format(owner='paddlepaddle', repo=repo) + '/%s' %PR + '/commits'
        response = requests.get(commitUrl)
        githubPR = response.json()[-1]['commit']['message'].split('_')[1].strip()
        return githubPR

    def prepareGiteeFiles(self, repo, commitid, branch, title, changeFiles):
        self.giteePaddlePath = self.giteePaddlePath.format(repo=repo)
        self.githubPaddlePath = self.githubPaddlePath.format(repo=repo)
        for file_type in changeFiles:
            if file_type == 'added':
                for filename in changeFiles[file_type]:
                    giteePaddlePath = self.giteePaddlePath + '/' + filename.replace(filename.split('/')[-1], '')
                    os.system('mkdir -p %s' % giteePaddlePath)
                    os.system('touch %s/%s' %(self.giteePaddlePath, filename))
                    os.system('cp -r %s/%s %s/%s' %(self.githubPaddlePath, filename, self.giteePaddlePath, filename))
            elif file_type == 'modified':
                for filename in changeFiles[file_type]:
                    os.system('cp -r %s/%s %s/%s' %(self.githubPaddlePath, filename, self.giteePaddlePath, filename))
            elif file_type == 'removed':
                for filename in changeFiles[file_type]:
                    print('remove file: %s/%s' %(self.giteePaddlePath, filename))
                    os.system('rm -rf %s/%s' %(self.giteePaddlePath, filename))
            elif file_type == 'renamed':
                for filename in changeFiles[file_type]:
                    old_name = filename.split(':')[0]
                    new_name = filename.split(':')[1]
                    os.system('mv %s/%s %s/%s' %(self.giteePaddlePath, old_name, self.giteePaddlePath, new_name))
    
    def create_pr(self, repo, branch, title, body):
        """
        create a pr
        return PR, commitId
        """
        prUrl = self.prUrl.format(owner='paddlepaddle', repo=repo)
        payload = {"access_token": "xxx"}
        data = {"title":"%s" %title,"head":"PaddlePaddle-Gardener:%s" %branch,"base":"develop","body":body}
        response = requests.request("POST", prUrl, params=payload, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        if response.status_code == 400 and '不存在差异' in response.json()['message']:
            return 1, 1
        else:
            count = 0
            while response.status_code not in [200, 201]:
                time.sleep(10)
                response = requests.request("POST", prUrl, params=payload, headers={'Content-Type': 'application/json'})
                count += 1
                if count >= 3:
                    break
            if response.status_code in [200, 201]:
                PR = response.json()['number']
                sha = response.json()['head']['sha']
                logger.info('Gitee PaddlePaddle/%s %s %s create success!' %(repo, PR, sha))
                return PR, sha
            else:
                title = '[告警]Gitee提交PR失败'
                receivers = ['zhangchunle@baidu.com']
                mail_content = 'repo: %s PR: %s, data: %s, %s' %(repo, prUrl, data, response.text)
                sendMail(title, mail_content, receivers)
                logger.error('Gitee PaddlePaddle/%s %s %s create failed!' %(repo, PR, sha))
                return None, None
        
class githubPrMigrateGitee():
    def __init__(self):
        self.giteePaddle = giteeRepo()
        self.githubPaddle = GithubRepo()
        self.changeFiles_default = []

    def ifPRconflict(self, changeFiles):
        """
        当天提交的PR是否可能有PR冲突
        """
        ifconflict = False
        changeFiles_list = []   
        for file_type in changeFiles:
            if file_type == 'renamed':
                for filename in changeFiles[file_type]:
                    changeFiles_list.append(filename.split(':')[0])
                    changeFiles_list.append(filename.split(':')[1])
            else:
                for filename in changeFiles[file_type]:
                    changeFiles_list.append(filename)
        for filename in changeFiles_list:
            if filename in self.changeFiles_default:
                ifconflict = True
                self.changeFiles_default = []
                break
            else:
                self.changeFiles_default.append(filename)
        if ifconflict == True:
            for filename in changeFiles_list:
                self.changeFiles_default.append(filename)
        return ifconflict

    def main(self, repo):
        gitee_merge_pr(repo)
        os.system('bash ./Paddle-bot/gitee/update_code.sh giteePaddle %s' %repo)
        os.system('bash ./Paddle-bot/gitee/update_code.sh githubPaddle %s' %repo)
        now = datetime.datetime.now()
        beforeTime = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
        print("beforeTime")
        print(beforeTime)
    
        #lastestCommit_gitee = self.giteePaddle.getlastestCommit(repo)
        #print(lastestCommit_gitee)
        #CommitList_github = self.githubPaddle.getCommitList(repo, lastestCommit_gitee, beforeTime)
        #print(CommitList_github)
    
        lastestPR_gitee = self.giteePaddle.getlastestPR(repo)
        GithubPR = self.giteePaddle.getGithubPRInlastestPR(repo, lastestPR_gitee)
        commitId_github = self.githubPaddle.getPRMergeCommit(repo, GithubPR)
        CommitList_github = self.githubPaddle.getCommitList(repo, commitId_github, beforeTime)
        for commitId in CommitList_github[::-1]:
            changeFiles, PR = self.githubPaddle.getPRchangeFiles(repo, commitId)
            ifconflict = self.ifPRconflict(changeFiles)
            if ifconflict == True:
                gitee_merge_pr(repo)
                time.sleep(10)
                os.system('bash ./Paddle-bot/gitee/update_code.sh giteePaddle %s' %repo) # merge后要更新环境
            branch, title, body = self.githubPaddle.getPRtitleAndBody(repo, PR)
            if branch == 'develop':
                branch = 'dev_pr_%s' %int(time.time())
            else:
                branch = '%s_%s' %(branch, int(time.time()))
            branch = branch.replace('/', '_')
            os.system('bash ./Paddle-bot/gitee/update_code.sh migrateEnv %s %s %s' %(repo, commitId, branch))
            self.giteePaddle.prepareGiteeFiles(repo, commitId, branch, title, changeFiles)
            os.system('bash ./Paddle-bot/gitee/update_code.sh prepareCode %s %s %s mirgate_%s' %(repo, commitId, branch, PR))
            PR, sha = self.giteePaddle.create_pr(repo, branch, title, body)
            if PR == 1 and sha == 1:
                continue 
            elif PR == None:
                break
            time.sleep(5)
        

if __name__ == '__main__':
    repo_list = ['PaddleHub', 'Paddle']
    for repo in repo_list:
        githubPrMigrateGitee().main(repo)


