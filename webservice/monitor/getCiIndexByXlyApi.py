"""
通过xly api获取CI指标: 有些ci指标第一时间拿不到
"""
import os
print(os.getcwd())
import sys
sys.path.append("..")
from utils.handler import xlyHandler

def getCIIndex():
    not_request_xlylog = open("../buildLog/not_request_xlylog.txt", 'r')
    not_request_xlylog_list = not_request_xlylog.readlines()
    print(not_request_xlylog_list)
    not_request_xlylog.close()
    not_request_xlylog_list = ['https://xly.bce.baidu.com/paddlepaddle/paddle/newipipe/detail/2343050/job/3307897']
    for target_url in not_request_xlylog_list:
        jobid = target_url.strip().split('/')[-1]
        handler = xlyHandler()
        ci_index_res = handler.getCIindex(jobid)
        print(ci_index_res.text)
        if len(ci_index_res.text) < 0:
            print(target_url)

getCIIndex()