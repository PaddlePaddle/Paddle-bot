# -*- coding: utf-8 -*-
import requests
import datetime


def getTodayDuty():
    today = datetime.date.today()
    duty_dict = {
        'Paddle': 'http://xxx:8091/v1/dutytable/onduty?dutytable_name=paddle',
        'Paddle-Lite':
        "http://xxx:8091/v1/dutytable/onduty?dutytable_name=lite",
        'PaddleOCR': "http://xxx:8091/v1/dutytable/onduty?dutytable_name=ocr"
    }
    for repo in duty_dict:
        url = duty_dict[repo]
        response = requests.get(url)
        assigee = response.json()['td']['github_id']
        with open("../buildLog/%s_todayDuty-%s.log" % (repo, today),
                  "wb") as f:
            f.write(str.encode(assigee))
            f.close()


def getAllDltpOnJob():
    today = datetime.date.today()
    url = 'http://xxx:8091/v1/user/person_info?name=&github_id=&status=在职&team=&token=bc9sazgnm5YyYRxz'
    response = requests.get(url).json()
    person_on_job = []
    with open("../buildLog/person_on_job-%s.log" % today, "wb") as f:
        for index in response:
            line = index['github_id'] + '\n'
            f.write(str.encode(line))
        f.close()


getTodayDuty()
getAllDltpOnJob()
