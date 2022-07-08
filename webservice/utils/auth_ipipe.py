#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import base64
import rsa
import json
import hashlib
import os


class xlyAuthorization(object):
    """
    效率云认证
    """

    def __init__(self):
        self.access_id = os.getenv("IPIPE_ACCESS_ID")
        self.serect = os.getenv("IPIPE_SECRET")
        self.session = requests.Session()

    def encrypt(self, pub, original_text):
        """公钥加密"""
        pub = rsa.PublicKey.load_pkcs1_openssl_pem(pub)
        crypt_text = rsa.encrypt(bytes(original_text.encode('utf-8')), pub)
        return crypt_text  # 加密后的密文

    def query_2_md5(self, param):
        m = hashlib.md5()
        m.update(bytes(param.encode('utf-8')))
        dig = m.hexdigest()
        return dig

    def set_sign(self, param):
        dig = self.query_2_md5(param)
        auth_string = self.encrypt(self.serect, dig)
        cipher_text = base64.b64encode(auth_string)
        cipher_str = str(cipher_text, encoding="utf-8")
        sign = "%s %s" % (self.access_id, cipher_str)
        return sign


class xlyOpenApiRequest(xlyAuthorization):
    """请求xly的openAPI"""

    def get_method(self,
                   url,
                   param='',
                   headers={"Content-Type": "application/json"}):
        """
        xly get http
        """
        req = requests.Request("GET", url, headers=headers).prepare()
        sign = self.set_sign(param)
        req.headers.update({'Authorization': sign})
        res = self.session.send(req, timeout=30)
        return res

    def post_method(self,
                    url,
                    data,
                    param='',
                    headers={"Content-Type": "application/json"}):
        """
        xly post http
        """
        req = requests.Request(
            "POST", url, data=data, headers=headers).prepare()
        sign = self.set_sign(param)
        req.headers.update({'Authorization': sign})
        res = self.session.send(req, timeout=15)
        return res


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
    cipher_str = str(cipher_text, encoding="utf-8")
    sign = "%s %s" % (access_id, cipher_str)
    return sign


def Get_ipipe_auth(url, query_param=''):
    session = requests.Session()
    req = requests.Request(
        "GET", url, headers={"Content-Type": "application/json"}).prepare()
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    return session, req


def Post_ipipe_auth(url, data, query_param=''):
    session = requests.Session()
    req = requests.Request(
        "POST", url, data=data,
        headers={"Content-Type": "application/json"}).prepare()
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    return session, req
