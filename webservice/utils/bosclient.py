#!/usr/bin/env python
#coding=utf-8

from baidubce.bce_client_configuration import BceClientConfiguration
from baidubce.auth.bce_credentials import BceCredentials
import os
from baidubce import exception
from baidubce.services import bos
from baidubce.services.bos import canned_acl
from baidubce.services.bos.bos_client import BosClient
from baidubce import exception

def uploading(context):
    bos_host = 'bj.bcebos.com'
    #BOS_ACCESS_KEY_ID = os.getenv("BOS_ACCESS_KEY_ID")
    #BOS_SECRET_ACCESS = os.getenv("BOS_SECRET_ACCESS")
    #bucket_name = os.getenv("bucket_name")
    BOS_ACCESS_KEY_ID = "019ba84033e647d48cf472895de88217"
    BOS_SECRET_ACCESS = "336b57c8f32a4b169c6bc812fb388e21"
    bucket_name = "paddle-docker-tar"
    config = BceClientConfiguration(credentials=BceCredentials(BOS_ACCESS_KEY_ID, BOS_SECRET_ACCESS), endpoint=bos_host)
    object_key = 'buildLog/%s' %context
    file_name = '/home/zhangchunle/Paddle-bot/webservice/buildLog/%s' %context
    bos_client = BosClient(config)
    isExist = IsExist(bos_client, bucket_name, object_key)
    if isExist == True:
        bos_client.delete_object(bucket_name, object_key)
    response = bos_client.put_object_from_file(bucket_name, object_key, file_name)
    print("update %s success" % (context))
    

def IsExist(bos_client, bucket_name, object_key):
    IsExist = False
    try:
        response = bos_client.get_object_meta_data(bucket_name, object_key)
        IsExist = True
    except exception.BceError as e:
        IsExist = False
    return IsExist