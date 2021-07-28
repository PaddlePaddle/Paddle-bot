import requests
import argparse
import sys
import re
import os

sys.path.append("..")
from utils.db import Database
from utils import bosclient


def GetCommits(headers, PR):
    commits_list = []
    url = 'https://api.github.com/repos/PaddlePaddle/Paddle/pulls/%s/commits' % PR
    response = requests.get(url, headers=headers).json()
    for commit in response:
        sha = commit['sha']
        if sha not in commits_list:
            commits_list.append(sha)
    return commits_list


def Info(sha):
    sql = "select fluidInferenceSize_so from paddle_ci_index where ciName='PR-CI-Inference' and commitId='%s' order by time desc limit 100;" % sha
    db = Database()
    data = list(db.query(sql))
    if data:
        size = data[0][0]['fluidInferenceSize_so']
        return size
    return False


def Save(sha, data, dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(dir_name + sha, "w+", encoding='utf-8') as f:
        f.write(str(data))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--PR', help='the day of dates.', default=None)
    args = parser.parse_args()
    headers = {'authorization': "token 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"}
    if args.PR:
        commits_list = GetCommits(headers, args.PR)
        for sha in commits_list:
            data = Info(sha)
            if data:
                Save(sha, data, '/home/zhangchunle/Paddle-bot/webservice/buildLog/%s/' % args.PR)
    bosclient.uploading(sha)
                
