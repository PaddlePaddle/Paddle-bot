#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
url1 = 'https://api.github.com/orgs/PaddlePaddle/repos'



a = 0
d = 0
headers = {'authorization': "token ca50067f736d45d1b5e8f943e559ea8923df3626"}
repos = requests.get(url1, headers = headers).json()
print(repos)
for r in repos:
    repo = r['name']
    url = 'https://api.github.com/repos/PaddlePaddle/%s/stats/code_frequency' %repo
    print(url)
    response = requests.get(url, headers = headers).json()
    if len(response)==0:
        response = requests.get(url, headers = headers).json()
    a1 = 0
    d1 = 0
    for week in response:
        if week[0] >= 1577808000 and week[0] <= 1612195200:
            a1 += week[1]
            d1 += week[2]
    print(a1)
    print(d1) 
    a += a1
    d += d1
print("total::")
print(a)
print(d)