#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import base64
import rsa
import json
import hashlib
import os

access_id = os.getenv("IPIPE_ACCESS_ID")
access_id = '4f93954b-75c9-4629-b053-c4bcc9f74eab'
serect = os.getenv("IPIPE_SECRET")
serect = '''-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDEfHbv2jtSj5/+tpBmNdBU7x01WQg2h0R7ys1OVQUTnxDruz0Yd0S3zanJ1E9hPf5ek9NO8m8vXq7nHgc/uSGr2waezL4vxQdRw1oTlU4k/aX/imiEOO+1z7brJqNmQcOvziDwHqtnjl9lEkF05/Sp9W/y2Fb0+dTvv36jFSPwxwIDAQAB
-----END PUBLIC KEY-----'''


def encrypt(pub, original_text):  # 用公钥加密
    pub = rsa.PublicKey.load_pkcs1_openssl_pem(pub)
    crypt_text = rsa.encrypt(bytes(original_text.encode('utf-8')), pub)
    return crypt_text  # 加密后的密文

def query_2_md5(query_param):
    m = hashlib.md5()
    m.update(bytes(query_param.encode('utf-8')))
    dig = m.hexdigest()
    return dig

def Sign(query_param):
    dig = query_2_md5(query_param)
    auth_string = encrypt(serect, dig)
    cipher_text = base64.b64encode(auth_string)
    cipher_str = str(cipher_text, encoding = "utf-8")
    sign = "%s %s" %(access_id, cipher_str)
    return sign

def Get_ipipe_auth(url, query_param=''):
    session = requests.Session()
    req = requests.Request("GET", url, headers= {"Content-Type": "application/json"}).prepare()
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    return session, req

def Post_ipipe_auth(url, data, query_param=''):
    session = requests.Session()
    req = requests.Request("POST", url, data=data, headers= {"Content-Type": "application/json"}).prepare()
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    return session, req