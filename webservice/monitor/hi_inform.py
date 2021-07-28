import json
import requests

with open("../buildLog/wait_task.json", 'r') as load_f:
    all_waiting_task = json.load(load_f)
    load_f.close()

print(all_waiting_task)

if len(all_waiting_task) == 0:
    Message = "Hi, 现在暂无linux任务排队。\n  您可用通过此链接 https://sugar.baidu-int.com/report/r_1013e-6hbpzy71-k9ywwo/5a822e2218abc2466a811c4c6bc2a574 查看自己正在运行的任务预计执行时间。"
else:
    v100_task = []
    p4_task = []
    mac_task = []
    win_task = []
    benchmark_task = []
    approval_task = []
    for task in all_waiting_task:
        if 'cardType' in task and task['cardType'].startswith('nTeslaV100'):
            v100_task.append(task) 
        elif 'cardType' in task and task['cardType'].startswith('nTeslaP4'):
            p4_task.append(task)
        else:
            if task['CIName'].startswith('PR-CI-Mac'):
                mac_task.append(task)
            elif task['CIName'].startswith('PR-CI-Windows'):
                win_task.append(task)
            elif 'Benchmark' in task['CIName']:
                benchmark_task.append(task)
            elif 'APPROVAL' in task['CIName']:
                approval_task.append(task)

    v100_length = len(v100_task)
    p4_length = len(p4_task)
    mac_length = len(mac_task)
    win_length = len(win_task)
    benchmark_length = len(benchmark_task)
    approval_length = len(approval_task)

    longest_v100 = '队末任务需排队%smin' %v100_task[v100_length - 1]['timeToStart'] if v100_length > 0 else '现在提交即可立刻开始执行'
    longest_p4 = '队末任务需排队%smin' %p4_task[p4_length - 1]['timeToStart'] if p4_length > 0 else '现在提交即可立刻开始执行'
    longest_mac = '队末任务需排队%smin' %mac_task[mac_length - 1]['timeToStart'] if mac_length > 0 else '现在提交即可立刻开始执行'
    longest_win = '队末任务需排队%smin' %win_task[win_length - 1]['timeToStart'] if win_length > 0 else '现在提交即可立刻开始执行'
    longest_benchmark = '队末任务需排队%smin' %benchmark_task[benchmark_length - 1]['timeToStart'] if benchmark_length > 0 else '现在提交即可立刻开始执行'
    longest_approval = '队末任务需排队%smin' %approval_task[approval_length - 1]['timeToStart'] if approval_length > 0 else '现在提交即可立刻开始执行'
    
    Message = "Hi, 现在排队任务共有%s个。其中: \n  V100任务（Coverage/Py3）共%s个，%s。\n  P4任务（CPU-Py2/Inference/FluidDoc1/测试ci等）共%s个，%s。\n  Mac任务（Mac/Mac-Python3）共%s个，%s。\n  Windows任务（Windows/Windows-OPENBLAS）共%s个，%s。\n  Benchmark任务（Benchmark）共%s个，%s。\n  APPROVAL任务（Paddle APPROVAL/Benchmark APPROVAL）共%s个，%s。\n  您可用通过此链接https://sugar.baidu-int.com/report/r_1013e-6hbpzy71-k9ywwo/5a822e2218abc2466a811c4c6bc2a574 查看自己的PR的预计排队时间。" %(len(all_waiting_task), v100_length, longest_v100, p4_length, longest_p4, mac_length, longest_mac, win_length, longest_win, benchmark_length, longest_benchmark, approval_length, longest_approval)
    print(Message)
    
url = "http://qyin.im.baidu.com/msgt/api/sendMsgToGroup?access_token=cd5db6ea6bee8cd6bb21d4d79ba50022"
data = json.dumps({"msg_type":"text", "access_token":"cd5db6ea6bee8cd6bb21d4d79ba50022", "to":1616610, "content": Message})
header = {"Content-Type": "application/json"}
r = requests.post(url, data=data, headers=header)
print(r.text)
