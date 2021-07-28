
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import time
import base64
#from Crypto.PublicKey import RSA
import rsa
import json
import hashlib

access_id = '4f93954b-75c9-4629-b053-c4bcc9f74eab'
srect = '''-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDEfHbv2jtSj5/+tpBmNdBU7x01WQg2h0R7ys1OVQUTnxDruz0Yd0S3zanJ1E9hPf5ek9NO8m8vXq7nHgc/uSGr2waezL4vxQdRw1oTlU4k/aX/imiEOO+1z7brJqNmQcOvziDwHqtnjl9lEkF05/Sp9W/y2Fb0+dTvv36jFSPwxwIDAQAB
-----END PUBLIC KEY-----'''


def encrypt(pub, original_text):  # 用公钥加密
    pub = rsa.PublicKey.load_pkcs1_openssl_pem(pub)
    crypt_text = rsa.encrypt(bytes(original_text.encode('utf-8')), pub)
    return crypt_text  # 加密后的密文


while True:
    #params = 'key=running'
    for params in ['key=running', 'key=sarunning', 'key=waiting', 'key=sawaiting']:
        url = 'https://xly.bce.baidu.com/open-api/ipipe/rest/v1/paddle-api/status?%s' %params
        req = requests.Request("GET", url, headers= {"Content-Type": "application/json", "IPIPE-UID": "Paddle-bot"}).prepare()
        m = hashlib.md5()
        m.update(bytes(params.encode('utf-8')))
        dig = m.hexdigest()
        auth_string = encrypt(srect, dig)
        cipher_text = base64.b64encode(auth_string)
        cipher_str = str(cipher_text, encoding = "utf-8")
        sign = "%s %s" %(access_id, cipher_str)
        req.headers.update({'Authorization': sign})
        s = requests.Session()
        #print(s)
        start = int(time.time())
        r = s.send(req)
        end = int(time.time())
        print('%s : %s' %(params, end-start))
        print(r)
        #print(r.text)
    time.sleep(10)