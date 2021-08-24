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
    获取员工相关信息
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
    if not page_num:
        page_num = 1
    return page_num


def get_number(url, headers, page_num, date):
    """
    获取符合要求的PR/Issue号
    """
    number_list = {}
    for page in range(page_num):
        page += 1
        page_url = url + '&page=' + str(page)
        res = requests.get(page_url, headers=headers, stream=True).json()
        for info in res:
            created_at = BJtime(info['created_at'])
            if created_at == date:
                number_list[info[
                    'number']] = [info['user']['login'], info['state']]
    return number_list


def get_comment(headers, number_list, date):
    """
    统计信息
    """
    user_dict = {}
    for number in number_list.keys():
        user_dict[number] = {}
        url = 'https://api.github.com/repos/PaddlePaddle/Paddle/pulls/%s/comments?per_page=100' % number
        response = requests.get(url, headers=headers).json()
        # 获取PR作者相关信息
        auther_info = getPersonnel(number_list[number][0])
        if auther_info:
            auther = auther_info[0]
            auther_email = auther_info[1]
            auther_team = auther_info[2]
        else:
            auther = number_list[number][0]
            auther_email = None
            auther_team = None
        for info in response:
            if info and info['user']['login'] != 'paddle-bot[bot]' and info[
                    'user']['login'] != number_list[number][0]:
                # 获取评审人相关信息
                user_info = getPersonnel(info['user']['login'])
                if user_info:
                    user = user_info[0]
                    email = user_info[1]
                    team = user_info[2]
                if email not in user_dict[number].keys():
                    user_dict[number][email] = [
                        number, user, email, team, number_list[number][1], 1,
                        auther, auther_email, auther_team
                    ]
                else:
                    user_dict[number][email][5] += 1
    result_df = pd.DataFrame()
    for num in user_dict.keys():
        df = pd.DataFrame(
            user_dict[num].values(),
            columns=[
                'num', 'user', 'email', 'team', 'state', 'count', 'pr_auther',
                'auther_email', 'auther_team'
            ])
        result_df = result_df.append(df)
    file_path = pd.ExcelWriter('./pr_datas/%s_pr_comments.xlsx' % date)
    result_df.fillna(' ', inplace=True)
    result_df.to_excel(
        file_path, encoding='utf-8', index=False, sheet_name="PR")
    file_path.save()
    return user_dict


if __name__ == '__main__':
    url = 'https://api.github.com/repos/PaddlePaddle/Paddle/pulls?per_page=100&state=all'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Authorization': 'token ',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--date', help='年-月', default='2021-07')
    args = parser.parse_args()
    page_num = get_page(url, headers)
    number_list = get_number(url, headers, page_num, args.date)
    user_dict = get_comment(headers, number_list, args.date)
    print(user_dict)
