import requests
import base64
import rsa
import json
import hashlib
import os

access_id = os.getenv("IPIPE_ACCESS_ID")
serect = os.getenv("IPIPE_SECRET")


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


def Get_ipipe_auth(url):
    session = requests.Session()
    req = requests.Request(
        "GET", url, headers={"Content-Type": "application/json"}).prepare()
    query_param = ''
    sign = Sign(query_param)
    req.headers.update({'Authorization': sign})
    return session, req
