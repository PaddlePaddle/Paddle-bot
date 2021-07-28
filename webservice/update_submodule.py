import os
import requests
import datetime
import json

def prepare_env(date):
    """prepare ENV"""
    current_dir = os.getcwd()
    des_dir = '%s/benchmark' %current_dir
    env_file = '%s/utils/update_third_benchmark.sh' % current_dir

    status = os.system('bash %s benchmark updateSubModule%s' % (env_file, date))
    return des_dir, status


def create_submodule_pr(repo):
    """create a pr to update submodule"""
    t = str(datetime.date.today()).replace('-', '')
    
    #des_dir, env_status = prepare_env(t)
    #print(des_dir, env_status)
    des_dir = '/home/zhangchunle/Paddle-bot/webservice/benchmark'
    env_status = 0
    if env_status == 0:
        today = datetime.date.today()
        url = 'https://api.github.com/repos/%s/pulls' % repo
        payload = {"title": "Update submodule in %s by PaddlePaddle-Gardener " %today, "head": "PaddlePaddle-Gardener:updateSubModule%s" %t, "base":"master", "body": "update submodule."}
        payload = json.dumps(payload)
        print(payload)
        headers = {
            'authorization': "Basic UGFkZGxlUGFkZGxlLUdhcmRlbmVyOm11c2ljamF5ODg2NjU5",
            'content-type': "application/json"
        }
        response = requests.request("POST", url, data=payload, headers=headers)
        print("response: %s" %response.status_code)
        print("response.text: %s" %response.text)
    os.rmdir(des_dir)
    
if __name__ == "__main__":
    create_submodule_pr('PaddlePaddle/benchmark')
    