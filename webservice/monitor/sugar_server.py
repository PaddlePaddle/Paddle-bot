from flask import Flask
from flask import request
import json

def get_all_running_task():
    with open("../buildLog/running_task.json", 'r') as load_f:
        all_running_task = json.load(load_f)
        load_f.close()
    data = {
        "status": 0,
        "msg": "",
        "data": {
            "total": 5,
            "columns": [
            {
                "name": "PR号",
                "id": "PR",
                "textAlign": "center"
            },
            {
                "name": "CI名字",
                "id": "CIName",
                "textAlign": "center"
            },
            {
                "name": "commitId",
                "id": "commitId",
                "textAlign": "center"
            },
            {
                "name": "repo",
                "id": "repoName",
                "textAlign": "center"
            },
            {
                "name": "已运行时间/min",
                "id": "running",
                "textAlign": "center"
            },
            {
                "name": "预计还需运行时间/min",
                "id": "stillneedTime",
                "textAlign": "center"
            }
            ],
            "rows": all_running_task
        }
    }
    return data


def get_all_waiting_task():
    with open("../buildLog/wait_task.json", 'r') as load_f:
        all_waiting_task = json.load(load_f)
        load_f.close()
    data = {
        "status": 0,
        "msg": "",
        "data": {
            "total": 5,
            "columns": [
            {
                "name": "PR号",
                "id": "PR",
                "textAlign": "center"
            },
            {
                "name": "CI名字",
                "id": "CIName",
                "textAlign": "center"
            },
            {
                "name": "commitId",
                "id": "commitId",
                "textAlign": "center"
            },
            {
                "name": "repo",
                "id": "repoName",
                "textAlign": "center"
            },
            {
                "name": "已等待时间/min",
                "id": "waiting",
                "textAlign": "center"
            },
            {
                "name": "预计还需等待时间/min",
                "id": "timeToStart",
                "textAlign": "center"
            }
            ],
            "rows": all_waiting_task
        }
    }
    return data
    

def get_filter_data(typ, queryKey):
    with open("../buildLog/wait_task.json", 'r') as load_f:
        all_waiting_task = json.load(load_f)
        load_f.close()
    filter_data = []
    for task in all_waiting_task:
        if task[typ].startswith(queryKey):
            filter_data.append(task)
    data = {
        "status": 0,
        "msg": "",
        "data": {
            "total": 5,
            "columns": [
            {
                "name": "PR号",
                "id": "PR",
                "textAlign": "center"
            },
            {
                "name": "CI名字",
                "id": "CIName",
                "textAlign": "center"
            },
            {
                "name": "commitId",
                "id": "commitId",
                "textAlign": "center"
            },
            {
                "name": "repo",
                "id": "repoName",
                "textAlign": "center"
            },
            {
                "name": "已等待时间/min",
                "id": "waiting",
                "textAlign": "center"
            },
            {
                "name": "预计还需等待时间/min",
                "id": "timeToStart",
                "textAlign": "center"
            }
            ],
            "rows": filter_data
        }
    }
    return data


def get_filter_data_all(PR, CIName):
    with open("../buildLog/wait_task.json", 'r') as load_f:
        all_waiting_task = json.load(load_f)
        load_f.close()
    filter_data = []
    for task in all_waiting_task:
        if task['PR'].startswith(PR) and task['CIName'].startswith(CIName):
            filter_data.append(task)
    data = {
        "status": 0,
        "msg": "",
        "data": {
            "total": 5,
            "columns": [
            {
                "name": "PR号",
                "id": "PR",
                "textAlign": "center"
            },
            {
                "name": "CI名字",
                "id": "CIName",
                "textAlign": "center"
            },
            {
                "name": "commitId",
                "id": "commitId",
                "textAlign": "center"
            },
            {
                "name": "repo",
                "id": "repoName",
                "textAlign": "center"
            },
            {
                "name": "已等待时间/min",
                "id": "waiting",
                "textAlign": "center"
            },
            {
                "name": "预计还需等待时间/min",
                "id": "timeToStart",
                "textAlign": "center"
            }
            ],
            "rows": filter_data
        }
    }
    return data

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def sugar_waitting_api():
    
    arguments = json.loads(request.data)
    if len(arguments['conditions']) == 1:
        if arguments['conditions'][0]['k'] == 'PR':
            PR = arguments['conditions'][0]['v']
            data = get_filter_data('PR', PR)
        elif arguments['conditions'][0]['k'] == 'CIName':
            CIName = arguments['conditions'][0]['v']
            data = get_filter_data('CIName', CIName)
    elif len(arguments['conditions']) == 2:
        for i in arguments['conditions']:
            if i['k'] == 'PR':
                PR = i['v']
            else:
                CIName = i['v']
        data = get_filter_data_all(PR, CIName)
    else:
        data = get_all_waiting_task()
    
    #data = '服务故障，请等待'
    return data


@app.route('/api/running', methods=['POST'])
def sugar_running_api():
    data = get_all_running_task()
    #data = '服务故障，请等待'
    return data



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088)
