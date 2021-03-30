#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
urllib.parse: 使用其中的quote函数，将字符串转换为url编码，避免信息中存在特殊字符导致传输截断、传输错误的问题
traceback: 打印不可预知的异常信息
requests: 发送get或post请求
datetime: 获取想要的日期时间
logging: 日志模块，记录日志
re: 使用正则匹配url返回信息中的页码
os: 用于使用系统命令和判断系统环境
"""


import urllib.parse
import traceback
import requests
import datetime
import logging
import time
import sys
import re
import os


sys.path.append("..")
from webservice.utils.mail_163 import Mail


class GithubIssueToGitee(object):
    """
    将github中的issue同步至gitee中
    StatusCode: 分别记录创建issue（title）和新建评论所返回的状态码，用于开发期间统计各个问题的出现概率
    """
    def __init__(self, repo=None, headers=None, create_token=None):
        self.yesterday, self.close_day = self.GetDate()
        logging.basicConfig(
                            level=logging.INFO,
                            filename='./logs/IssueToGitee_%s.log' % self.yesterday,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                            )
        self.repo_path = repo
        self.headers = headers
        self.create_token = create_token
        self.owner = self.repo_path.split('/')[0]
        self.repo = self.repo_path.split('/')[1]
        self.logger = logging.getLogger(__name__)
        self.issue_list = self.GetGihubIssue()
        self.issues_dict = iter(self.GetIssueinfo())
        self.request_result = {'issue':{}, 'comment':{}}
        

    def utcTimeToStrTime(self, utcTime):
        """
        utc时间转换为当地时间
        """
        UTC_FORMAT = r"%Y-%m-%dT%H:%M:%SZ"
        utcTime = datetime.datetime.strptime(utcTime, UTC_FORMAT)
        localtime = utcTime + datetime.timedelta(hours=8)
        result = datetime.datetime.strftime(localtime, r'%Y-%m-%d')
        return result


    def GetDate(self):
        """
        获取时间
        """
        today = datetime.datetime.today()
        oneday = datetime.timedelta(days=1)
        yesterday = today - oneday
        close_day = yesterday - oneday
        yesterday = datetime.datetime.strftime(yesterday, r'%Y-%m-%d')
        close_day = datetime.datetime.strftime(close_day, r'%Y-%m-%d')
        return yesterday, close_day


    def PageUrl(self):
        """
        获取返回信息中的总页数
        """
        try:
            url = "https://api.github.com/repos/" + self.repo_path + '/issues?state=closed&per_page=100'
            msg = requests.get(url, headers=self.headers)
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
            page_num = re.search(r'&page=(\d+)', num)
            total_pages = int(page_num.group(1))
            self.logger.info("Total pages: %s" % (total_pages))
        except BaseException:
            self.logger.error("Failed to request the total number of pages %s" % (url))
            self.sendMail("Failed to request the total number of pages %s" % (url))
        return url, total_pages
        

    def GetGihubIssue(self):
        """
        获取issue号, 记录在文件
        data_path: 记录issue的文件
        记录已经迁移的issue
        """
        data_path = './datas/github_list%s.txt' % self.yesterday
        if os.path.exists(data_path):
            if not os.path.getsize(data_path):
                self.logger.info("%s has no new issues" % self.yesterday)
                msg = "github昨日无新增closed状态的issue"
                self.sendMail(msg, title="issue迁移完成")
                exit()
            with open(data_path, 'r', encoding='utf-8') as f:
                issue_list = f.read().split(',')
                self.logger.info("Read the issue list file successfully")
                return issue_list
        else:
            url, page_num = self.PageUrl()
            issue_list = []
            for page in range(page_num):
                page += 1
                result_url = url + '&page=' + str(page)
                try:
                    response = requests.get(result_url, headers=self.headers).json()
                    for idex in range(len(response)):
                        """比对closed_at的时间"""
                        closed_at = self.utcTimeToStrTime(response[idex]['closed_at'])
                        if closed_at == self.yesterday and "pull_request" not in response[idex].keys():
                            issue_list.append(response[idex]['number'])
                except BaseException:
                    self.logger.error("Failed to request issues %s"%(result_url))
                    self.sendMail("Failed to request issues %s"%(result_url))
            issue_list = sorted(issue_list)
            f = open(data_path, 'w', encoding='utf-8')
            f.write(str(issue_list).replace('[', '').replace(']', ''))
            f.close()
            self.logger.info("Issue list file %s" % data_path)
            return issue_list


    def GetIssueinfo(self):
        """
        获取issue相关信息
        info_dict:{
            num: github中issue号
            title: issue标题
            body: issue描述
            issue_url: issue的url地址，方便于阅读人点击跳转查看原文
            author: issue作者
            comments: 存储该issue下所有评论的列表
            labels: 存储该issue所属标签的列表
        }
        """
        for num in self.issue_list:
            info_dict = {}
            title_url = 'https://api.github.com/repos/%s/issues/%s' % (self.repo_path, num)
            title_response = requests.get(title_url, headers=self.headers).json()
            self.logger.info("Start sync issue %s" % (num))
            info_dict['num'] = num
            info_dict['title'] = title_response['title']
            info_dict['body'] = urllib.parse.quote(title_response['body'])
            info_dict['issue_url'] = title_response['html_url']
            info_dict['author'] = title_response['user']['login']
            info_dict['comments'] = []
            info_dict['labels'] = []
            if title_response['labels']:
                for label in title_response['labels']:
                    info_dict['labels'].append(label['name'])
            self.logger.info("Get %s issue's information successfully!!!" % (num))
            comments_url = title_url + "/comments"
            comments_response = requests.get(comments_url, headers=self.headers).json()
            for comment in comments_response:
                info_dict['comments'].append([comment['user']['login'],
                                            urllib.parse.quote(comment['html_url']),
                                           urllib.parse.quote(comment['body'])])
                self.logger.info("Get comment's information successfully！---> %s" % (info_dict))
            yield info_dict

  
    def _CreateCommentToGitee(self, issue_num, comments_list):
        """
        将issue评论同步至gitee中
        """
        for comment_info in comments_list:
            if 'counts' in self.request_result['comment']:
                self.request_result['comment']['counts'] += 1
            else:
                self.request_result['comment']['counts'] = 1
            create_comment_url = "https://gitee.com/api/v5/repos/%s/issues/%s/comments?access_token=%s&body=[<b> 源自github用户%s</b>](%s): \r\n%s" \
                                        % (self.repo_path, issue_num, self.create_token, 
                                            comment_info[0], comment_info[1], comment_info[2])
            comment_response = requests.post(create_comment_url)
            CommentStatus = comment_response.status_code
            if CommentStatus != 201:
                self.logger.error("Status code %s, %s" % (CommentStatus, comment_response.text))
                break
            self.logger.info("Send a new comment request %s" % (create_comment_url))
            if CommentStatus in self.request_result['comment']:
                self.request_result['comment'][CommentStatus] += 1
            else:
                self.request_result['comment'][CommentStatus] = 1
            self.logger.info("Create comment %s" % (self.request_result['comment']))
        self.logger.info("The comment for creating issue %s is complete" % (issue_num))


    def _AssignLabels(self, issue_num, token, label_list):
        """
        gitee label只支持小于等于20大于等于2的字符
        创建issue时，api只支持以字符串的形式给label传参
        将列表转换成字符串，以，分割
        """
        for label in label_list:
            if len(label) < 2 and len(label) > 20:
                label_list.remove(label)
        str_lables = ",".join(label_list)
        if " " in str_lables:
            str_lables = str_lables.replace(" ", "_")
        assign_labels_url = "https://gitee.com/api/v5/repos/%s/issues/%s?access_token=%s&repo=%s&labels=%s" \
                            % (self.owner, issue_num, token, self.repo, str_lables)
        response = requests.patch(assign_labels_url)
        self.logger.info("Issue %s has been labelled" % issue_num)
        return response.status_code

    
    def _ClosedIssue(self, issue_num, token):
        """
        将issue状态改为closed
        """
        closed_issue_url = "https://gitee.com/api/v5/repos/%s/issues/%s?access_token=%s&repo=%s&state=closed" \
                                    % (self.owner, issue_num, token, self.repo)
        response = requests.patch(closed_issue_url)
        self.logger.info("Issue %s is closed" % issue_num)
        return response.status_code


    def _CompareLenth(self, msg):
        """
        判断字符是否超限
        """
        if type(msg) == 'list':
            for i in msg:
                if len(i) >= 15534:
                    return False
                else:
                    return True
        elif type(msg) == 'str':
            if len(msg) >= 15534:
                return False
            else:
                return True

    
    def sendMail(self, content, title="isuee迁移异常", receivers="iducn3@163.com"):
        mail = Mail()
        mail.set_sender('paddlepaddle_bot@163.com')
        mail.set_receivers(receivers)
        mail.set_title(title)
        mail.set_message(content, messageType='html', encoding='gb2312')
        mail.send()


    def CreateIssueToGitee(self, close_token):
        """
        将issue同步至gitee中
        """
        """创建issue"""
        yesterday_path = './datas/gitee_list%s' + self.yesterday
        close_path = './datas/gitee_list%s' + self.close_day
        github_list = []
        gitee_list = []
        for issue in self.issues_dict:
            if not self._CompareLenth(issue['comments']) or not self._CompareLenth(issue['body']):
                self.logger.error("Issue %s's description or commentexceeds the word limit" % issue['num'])
                self.sendMail("Issue %s's description or commentexceeds the word limit" % issue['num'])
                continue
            if 'counts' in self.request_result['issue']:
                self.request_result['issue']['counts'] += 1
            else:
                self.request_result['issue']['counts'] = 1
            Count = 0
            while Count < 3:
                create_issue_url = "https://gitee.com/api/v5/repos/%s/issues?access_token=%s&repo=%s&title=%s&body=[<b>源自github用户%s</b>](%s): \r\n%s" \
                                    % (self.owner, self.create_token, self.repo, 
                                    issue['title'], issue['author'], issue['issue_url'], issue['body'])
                try:
                    create_response = requests.post(create_issue_url)
                    IssueStatus = create_response.status_code
                    response_json = create_response.json()
                    if IssueStatus in self.request_result['issue']:
                        self.request_result['issue'][IssueStatus] += 1
                    else:
                        self.request_result['issue'][IssueStatus] = 1
                    self.logger.info("Create issue %s" % (self.request_result['issue']))

                    """新建issue的number"""
                    issue_num = response_json['number']
                    github_list.append(issue['num'])
                    gitee_list.append(issue_num)
                    self.logger.info("Send a new issue request:%s, Issue number:%s" 
                                    % (create_issue_url, issue_num))

                    """添加评论"""
                    self._CreateCommentToGitee(issue_num, issue['comments'])
                    self.logger.info("Issue %s creation completed" % (issue['num']))

                    """分配标签"""
                    if issue["labels"]:
                        self._AssignLabels(issue_num, close_token, issue["labels"])
                    Count = 3
                    
                            
                except Exception:
                    """
                    当状态为200或201，异常的原因是转换json失败
                    """
                    if IssueStatus == 200 or IssueStatus == 201:
                        traceback.print_exc()
                        Count = 3
                    elif IssueStatus == 403:
                        Count += 1
                        self.logger.error("Issue %s %s creation failed, status code %s, retry %s"
                                    % (issue['num'], issue['title'], IssueStatus, Count))
                        time.sleep(1)
                        if Count == 3:
                            self.logger.error("Issue %s retry %s times, all failed, status code %s"
                                    % (issue['num'], Count, IssueStatus))
                            self.sendMail("Issue %s retry %s times, all failed, status code %s"
                                    % (issue['num'], Count, IssueStatus))
                    else:
                        self.logger.error("Issue %s creation failed, status code %s, %s"
                                    % (issue['num'], IssueStatus, create_response.text))
                        self.sendMail("Issue %s creation failed, status code %s, %s"
                                    % (issue['num'], IssueStatus, create_response.text))
                        Count = 3
                time.sleep(1)

        """发邮件"""
        msg = "github issue迁移完成 \r\ngithub: %s\r\ngitee: %s" %(github_list, gitee_list)
        self.sendMail(msg, title="issue迁移完成")
        """按日期记录当日创建的issue，方便之后更新状态为closed的操作"""
        if gitee_list:
            f = open(yesterday_path, 'w', encoding='utf-8')
            f.write(str(gitee_list).replace('[', '').replace(']', ''))
            f.close()
        self.logger.info("The following issues have been migrated %s" 
                            % (self.issue_list))
        """将超过两天的issue状态改为closed"""
        if os.path.exists(close_path):
            with open(yesterday_path, 'r', encoding='utf-8') as f:
                close_list = f.read().split(',')
                self.logger.info("Read the issue list file successfully")
                for num in close_list:
                    self._ClosedIssue(num, close_token)
                msg = "issue%s，展示超过两天，已自动closed" % close_list
                self.sendMail(msg, title="issue自动closed")