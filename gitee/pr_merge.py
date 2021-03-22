from handler import GiteePROperation
import json


def gitee_merge_pr():
    with open('Paddle-bot/gitee/commitmap.json', 'r') as f:
        data = json.load(f)
        f.close()
    merge_pr_list = []
    for key in data:
        merge_pr_list.append(key)
    merge_pr_list.sort()
    for PR in merge_pr_list:
        GiteePROperation().merge('paddlepaddle', 'Paddle', PR)
