#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将github中的label同步至gitee中
"""


import urllib.parse
import traceback
import requests
import datetime
import logging
import re
import os


class GithubLabelToGitee(object):
    def __init__(self, repo, github_headers, token):
        self.repo = repo
        self.github = github_headers
        self.Token = token
        logging.basicConfig(
                            level=logging.INFO,
                            filename='./logs/GithubToGitee.log',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                            )
        self.logger = logging.getLogger(__name__)


    def _PageUrl(self, url, headers):
        """
        获取返回信息中的总页数
        """
        try:
            msg = requests.get(url, headers=headers)
            # 获取头信息中的Link内容
            if "Link" in msg.headers:
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
                page_num = re.search(r'page=(\d+)', num)
                total_pages = int(page_num.group(1))
                self.logger.info("Total pages: %s" % (total_pages))
                return total_pages
        except BaseException:
            self.logger.error("Failed to request the total number of pages %s" % (url))
        return False


    def GetGithubLabel(self):
        """
        获取github中所有label的名字和颜色
        """
        label_list = []
        label_url = 'https://api.github.com/repos/%s/labels?per_page=100' % self.repo
        page_num = self._PageUrl(label_url, self.github)
        if page_num:
            for page in range(page_num):
                page += 1
                label_response = requests.get(label_url + "&page=" + page, headers=self.github).json()
        else:
            label_response = requests.get(label_url, headers=self.github).json()
        for label in label_response:
            label_list.append([label['name'], label['color']])
        return label_list


    def CreateGiteeLabel(self):
        """
        在gitee中创建对应的label
        """
        label_list = self.GetGithubLabel()
        for label in label_list:
            if " " in label[0]:
                label[0] = label[0].replace(" ", "_")
            create_response = requests.post('https://gitee.com/api/v5/repos/%s/labels?access_token=%s&name=%s&color=%s' \
                                            % (self.repo, self.Token, label[0], label[1]))
            if create_response.status_code != 201 and \
                    create_response.status_code != 409:
                self.logger.error("Label %s creation failed, status code %s, failure reason: %s" \
                                % (label[0], create_response.status_code, create_response.text))
        self.logger.info("All labels are created")

