import pandas as pd
import datetime
import requests
import argparse
import time
import re


def BJtime(mergeTime):
    """
    utc时间转换北京时间
    """
    mergeTime = mergeTime.replace('T', ' ').replace('Z', '')
    mergeTime = datetime.datetime.strptime(mergeTime, '%Y-%m-%d %H:%M:%S')
    mergeTime = mergeTime + datetime.timedelta(hours=8)
    mergeTime = datetime.datetime.strftime(mergeTime, '%Y-%m')
    return mergeTime

def getPersonnel(user):
    """
    判断是否为内部员工
    """
    personnel_api = ''
    # 部门员工信息平台api--->按名字查询
    isname = requests.get(personnel_api + '?github_name=' + user).json()
    # 部门员工信息平台api--->按ID查询
    isID = requests.get(personnel_api + '?github_id=' + user).json()
    if isname:
        return [isname[0]['name'], isname[0]['email'], isname[0]['team']]
    elif isID:
        return [isID[0]['name'], isID[0]['email'], isID[0]['team']]
    return False

def get_page(url, headers):
    """
    获取总页数
    """
    page_num = 0
    response = requests.get(url, headers=headers, stream=True)
    try:
        if "Link" in response.headers.keys():
            # 获取头信息中的Link内容
            header_info = response.headers["Link"]
            # 消除<>和空格
            header_replace = re.sub('<|>| ', '', header_info)
            # 以,和;分割成一个列表
            header_split = re.split(',|;', header_replace)
            # 获取列表中rel="last"的索引
            last_index = header_split.index('rel=\"last\"')
            # 获取last的url链接
            num = header_split[last_index - 1]
            # 获取last的url中的页码
            page_num = int(re.search('&page=(\d+)', num).group(1))
    except BaseException as e:
        print(url)
    if not page_num:
        page_num = 1
    return page_num

def toFile(path, msg):
    with open(path, "w+", encoding='utf-8') as f:
        f.write(msg)

def get_info(url, headers, page_num, date):
    user_dict = {}
    for page in range(page_num):
        page += 1
        page_url = url + '&page=' + str(page)
        res = requests.get(page_url, headers=headers, stream=True).json()
        for info in res:
            if 'merged_at' in info.keys() and info['merged_at']:
                mergeTime = BJtime(info['merged_at'])
                if mergeTime == date:
                    user_info = getPersonnel(info['user']['login'])
                    if user_info:
                        user = user_info[0]
                        email = user_info[1]
                        team = user_info[2]
                        pr_num = info['number']
                        pr_url = info['url']
                        pr_res = requests.get(pr_url, headers=headers).json()
                        if email not in user_dict.keys():
                            user_dict[email] = [user, email, team, 1, pr_res['additions'], pr_res['deletions']]
                        else:
                            user_dict[email][3] += 1
                            user_dict[email][4] += pr_res['additions']
                            user_dict[email][5] += pr_res['deletions']
    print(user_dict)
    df = pd.DataFrame(user_dict.values(), columns=['name', 'email', 'team', 'PR数量', 'additions', 'deletions'])
    file_path = pd.ExcelWriter('./%s_contribution.xlsx' % date)
    df.fillna(' ', inplace=True)
    df.to_excel(file_path, encoding='utf-8', index=False, sheet_name="个人贡献量统计")
    file_path.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--date', help='年-月', default='2021-07')
    args = parser.parse_args()
    url = 'https://api.github.com/repos/PaddlePaddle/Paddle/pulls?state=closed&per_page=100'
    headers = {'User-Agent': 'Mozilla/5.0',
                'Authorization': 'token i',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
                }

    page_num = get_page(url, headers)
    res = get_info(url, headers, page_num, args.date)
