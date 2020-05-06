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
            if CHECK_CI in reponse[i]['commit']['message'] or len(CHECK_CI) == 0:
                res = True
    return res

def re_rule(body, CHECK_TEMPLATE):
    PR_RE = re.compile(CHECK_TEMPLATE, re.DOTALL)
    result = PR_RE.search(body)
    return result

def checkPRTemplate(body, CHECK_TEMPLATE, CHECK_TEMPLATE_doc=None):
    """
    Check if PR's description meet the standard of template
    Args:
        body: PR's Body.
        CHECK_TEMPLATE: check template str.
    Returns:
        res: True or False
    """
    res = False
    if CHECK_TEMPLATE_doc != None:
        print(CHECK_TEMPLATE_doc)
        note1 = '<!-- ADD SCREENSHOT HERE IF APPLICABLE. -->'
        note2 = '<!-- DESCRIBE THE BUG OR REQUIREMENT HERE. eg. #2020（格式为 #Issue编号）-->'
        body_no_note = re.sub(note2, "", re.sub(note1, "", body))
        doc_check = "- PR changes:（改动点）is \(\s*[A-D]*[C][A-D]*\s*\):"
        match_doc = re.search(doc_check, body, re.M|re.I)
        print(match_doc)
        if match_doc != None:
            result_doc = re_rule(body_no_note, CHECK_TEMPLATE_doc)
            if result_doc != None:
                res = True
            return res

    result = re_rule(body, CHECK_TEMPLATE)
    if len(CHECK_TEMPLATE) == 0 and len(body) == 0:
        res = False
    elif result != None:
        res = True
    return res