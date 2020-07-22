import requests
import re


def checkPRNotCI(commit_url, sha):
    """
    Check if PR's commit message can trigger CI.
    Args:
        commit_url(url): PR's commit url.
        sha(str): PR's commit code. (The only code provided by GitHub)
    Returns:
        res: True or False
    """
    res = False
    reponse = requests.get(commit_url).json()
    for i in range(0, len(reponse)):
        if reponse[i]['sha'] == sha:
            if 'notest' in reponse[i]['commit']['message']:
                res = True
    return res


def re_rule(body, CHECK_TEMPLATE):
    PR_RE = re.compile(CHECK_TEMPLATE, re.DOTALL)
    result = PR_RE.search(body)
    return result


def parameter_accuracy(body):
    PR_dic = {}
    PR_types = [
        'New features', 'Bug fixes', 'Function optimization',
        'Performance optimization', 'Breaking changes', 'Others'
    ]
    PR_changes = ['OPs', 'APIs', 'Docs', 'Others']
    body = re.sub("\r\n", "", body)
    type_end = body.find('### PR changes')
    changes_end = body.find('### Describe')
    PR_dic['PR types'] = body[len('### PR types'):type_end]
    PR_dic['PR changes'] = body[type_end + 14:changes_end]
    message = ''
    for key in PR_dic:
        test_list = PR_types if key == 'PR types' else PR_changes
        test_list_lower = [l.lower() for l in test_list]
        value = PR_dic[key].strip().split(',')
        single_mess = ''
        if len(value) == 1 and value[0] == '':
            message += '%s should be in %s. but now is None.' % (key,
                                                                 test_list)
        else:
            for i in value:
                i = i.strip().lower()
                if i not in test_list_lower:
                    single_mess += '%s.' % i
            if len(single_mess) != 0:
                message += '%s should be in %s. but now is [%s].' % (
                    key, test_list, single_mess)
    return message


def checkPRTemplate(repo, body, CHECK_TEMPLATE):
    """
    Check if PR's description meet the standard of template
    Args:
        body: PR's Body.
        CHECK_TEMPLATE: check template str.
    Returns:
        res: True or False
    """
    res = False
    note = r'<!-- Demo: https://github.com/PaddlePaddle/Paddle/pull/24810 -->\r\n|<!-- One of \[ New features \| Bug fixes \| Function optimization \| Performance optimization \| Breaking changes \| Others \] -->|<!-- One of\t\[ OPs \| APIs \| Docs \| Others \] -->|<!-- Describe what this PR does -->'
    body = re.sub(note, "", body)
    result = re_rule(body, CHECK_TEMPLATE)
    message = ''
    if len(CHECK_TEMPLATE) == 0 and len(body) == 0:
        res = False
    elif result != None:
        if repo in ['lelelelelez/leetcode', 'PaddlePaddle/Paddle']:
            message = parameter_accuracy(body)
            res = True if message == '' else False
        else:
            res = True
    elif result == None:
        res = False
        if repo in ['lelelelelez/leetcode', 'PaddlePaddle/Paddle']:
            message = parameter_accuracy(body)
    return res, message




def checkCIState(combined_statuses_url):
    res = False
    response = requests.get(combined_statuses_url).json()
    if response['state'] == "success":
        res = True
    return res
