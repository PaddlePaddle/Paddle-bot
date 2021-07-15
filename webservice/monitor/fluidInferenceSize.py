import requests
import sys
import re
import os

sys.path.append("xx")
from utils.db import Database
from utils import bosclient


def PageNum(headers):
    """
    获取返回信息中的总页数
    """
    url = "https://api.github.com/repos/PaddlePaddle/Paddle/pulls?state=closed&per_page=100&sort=merged_at"
    msg = requests.get(url, headers=headers)
    # 获取头信息中的Link内容
    header_info = msg.headers["Link"]
    # 消除<>和空格
    header_replace = re.sub('<|>| ', '', header_info)
    # 以,和;分割成一个列表
    header_split = re.split(',|;', header_replace)
    # 获取列表中rel="last"的索引
    last_index = header_split.index('rel=\"last\"')
    # 获取last的url链接
    num = header_split[last_index - 1]
    # 获取last的url中的页码
    page_num = re.search('&page=(\d+)', num)
    page_num = str(page_num.group(1))
    url = url + "&page=" + page_num
    return url


def Record_PR(PR):
    """
    记录已经获取过数据的PR
    """
    with open(dir_path + 'xx', "a+", encoding='utf-8') as f:
        f.write("%s," % str(PR))


def GetCommits(headers, url, dir_path):
    """
    获取PR中的commit ID
    """
    response = requests.get(url, headers=headers).json()
    commits_list = []
    for info in response:
        PR = str(info['number'])
        f = open(dir_path + 'xx', "r", encoding='utf-8')
        if PR not in f.read():
            Record_PR(PR)
            url = 'https://api.github.com/repos/PaddlePaddle/Paddle/pulls/%s/commits' % PR
            commit_response = requests.get(url, headers=headers).json()
            for commit in commit_response:
                sha = commit['sha']
                if sha not in commits_list:
                    commits_list.append(sha)
        f.close()
    return commits_list


def Info(sha):
    """
    从数据库中获取该信息
    """
    sql = "select fluidInferenceSize_so from paddle_ci_index where ciName='PR-CI-Inference' and commitId='%s' order by time desc limit 100;" % sha
    db = Database()
    data = list(db.query(sql))
    if data:
        size = data[0][0]['fluidInferenceSize_so']
        return size
    return False


def Save(data, dir_path):
    """
    保存fluidInference_so_size数据
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(
            dir_path + "fluidInference_so_size", "w+", encoding='utf-8') as f:
        f.write(str(data))


if __name__ == '__main__':
    headers = {'authorization': "token xx"}
    dir_path = 'xx'
    url = PageNum(headers)
    commits_list = GetCommits(headers, url, dir_path)
    for sha in commits_list:
        data = Info(sha)
        if data:
            print(sha)
            print(data)
            Save(data, dir_path)
            bosclient.uploading("fluidInference_so_size")
