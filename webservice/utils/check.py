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

def checkPRTemplate(body, CHECK_TEMPLATE):
    """
    Check if PR's description meet the standard of template
    Args:
        body: PR's Body.
        CHECK_TEMPLATE: check template str.
    Returns:
        res: True or False
    """
    res = False
    PR_RE = re.compile(CHECK_TEMPLATE, re.DOTALL)
    result = PR_RE.search(body)
    if len(CHECK_TEMPLATE) == 0 and len(body) == 0: 
        res = False    
    elif result != None:
        res = True
    return res

