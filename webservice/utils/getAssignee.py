import requests
import datetime
import bosclient

def getTodayDuty():
    today = datetime.date.today()
    duty_dict = {
        #'Paddle': 'http://10.88.148.15:8090/v1/duty/info',
        #'Paddle-Lite': "http://10.88.148.15:8090/v1/duty_lite/info"
        'Paddle': 'http://10.24.2.236:8090/v1/duty/info',
        'Paddle-Lite': "http://10.24.2.236:8090/v1/duty_lite/info",
        'PaddleOCR': "http://10.24.2.236:8090/v1/duty_ocr/info"
    }
    for repo in duty_dict:
        print(repo)
        url = duty_dict[repo]
        response = requests.get(url)
        print(response)
        #print(response.text)
        assigee = response.json()['td']['github_id']
        print(assigee)
        with open("../buildLog/%s_todayDuty-%s.log" %(repo, today), "wb") as f:
            f.write(assigee)
            f.close()
            bosclient.uploading("%s_todayDuty-%s.log" %(repo, today))
        
getTodayDuty()
