import requests
import re


def checkPRCI(commit_url, sha, CHECK_CI):
    """
    Check if PR's commit message can trigger CI.
    Args:
        commit_url(url): PR's commit url.
        sha(str): PR's commit code. (The only code provided by GitHub)
        CHECK_CI(str): PR's commit message checker.
    Returns:
        res: True or False
    """
    res = False
    reponse = requests.get(commit_url).json()
    for i in range(0, len(reponse)):
        if reponse[i]['sha'] == sha:
            if CHECK_CI in reponse[i]['commit']['message'] or len(
                    CHECK_CI) == 0:
                res = True
    return res


def re_rule(body, CHECK_TEMPLATE):
    PR_RE = re.compile(CHECK_TEMPLATE, re.DOTALL)
    result = PR_RE.search(body)
    return result


def checkPRTemplate(repo, body, CHECK_TEMPLATE, CHECK_TEMPLATE_doc=None):
    """
    Check if PR's description meet the standard of template
    Args:
        body: PR's Body.
        CHECK_TEMPLATE: check template str.
    Returns:
        res: True or False
    """
    res = False
    if repo in ['lelelelelez/leetcode', 'PaddlePaddle/Paddle']:
        note = '\*\*|<!-- ADD SCREENSHOT HERE IF APPLICABLE. -->|<!-- DESCRIBE THE BUG OR REQUIREMENT HERE. eg. #2020（格式为 #Issue编号）-->|-----------------------'
        body = re.sub(note, "", body)
        if CHECK_TEMPLATE_doc != None:
            doc_check = "- PR changes（改动点）is \(\s*[A-D]*[C][A-D]*\s*\):"
            match_doc = re.search(doc_check, body, re.M | re.I)
            if match_doc != None:  #choose doc changes
                others = "- Please write down other information you want to tell reviewers.(.*[^\s].*)"
                if re_rule(body, others) == None:
                    body = re.sub(
                        '- Please write down other information you want to tell reviewers.',
                        "", body)
                    CHECK_TEMPLATE_doc = "#### Required（必填, multiple choices, two at most）\r\n- PR type（PR 类型） is \(\s*[A-F]+\s*\):(.*?)- PR changes（改动点）is \(\s*[A-D]*[C][A-D]*\s*\):(.*?)- Use one sentence to describe what this PR does.（简述本次PR的目的和改动）(.*[^\s].*)#### Optional（选填, If None, please delete it）(.*?)- If you modified docs, please make sure that both Chinese and English docs were modified and provide a preview screenshot. （文档必填）(.*[^\s].*)"
                result_doc = re_rule(body, CHECK_TEMPLATE_doc)
                if result_doc != None:
                    res = Trues
                return res

        option_check = "#### Optional（选填, If None, please delete it）"
        match_option = re.search(option_check, body, re.M | re.I)
        if match_option == None:
            CHECK_TEMPLATE = "#### Required（必填, multiple choices, two at most）\r\n- PR type（PR 类型） is \(\s*[A-F]+\s*\):(.*?)- PR changes（改动点）is \(\s*[A-D]+\s*\):(.*?)- Use one sentence to describe what this PR does.（简述本次PR的目的和改动）(.*[^\s].*)"
        result = re_rule(body, CHECK_TEMPLATE)
        if len(CHECK_TEMPLATE) == 0 and len(body) == 0:
            res = False
        elif result != None:
            res = True
    else:
        result = re_rule(body, CHECK_TEMPLATE)
        if len(CHECK_TEMPLATE) == 0 and len(body) == 0:
            res = False
        elif result != None:
            res = True
    return res
