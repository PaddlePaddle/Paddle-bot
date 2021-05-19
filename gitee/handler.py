import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    filename='./logs/pr.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GiteePROperation():
    def __init__(self):
        self.prUrl = 'https://gitee.com/api/v5/repos/{owner}/{repo}/pulls'
        self.prMergeUrl = self.prUrl + '/{number}/merge'
        self.access_token = "xxxxx"

    def merge(self, owner, repo, number):
        prMergeUrl = self.prMergeUrl.format(
            owner=owner, repo=repo, number=number)
        payload = {
            "access_token": self.access_token,
            "merge_method": "squash",
            "prune_source_branch": "true"
        }
        r = requests.request(
            "PUT",
            prMergeUrl,
            params=payload,
            headers={'Content-Type': 'application/json'})
        print(r.text)
        return r.status_code

    def getPRListWithOpenStatus(self, owner, repo):
        PRList = []
        prUrl = self.prUrl.format(owner=owner, repo=repo)
        payload = {
            "access_token": self.access_token,
            "per_page": 100,
            "state": "open"
        }
        r = requests.request(
            "GET",
            prUrl,
            params=payload,
            headers={'Content-Type': 'application/json'})
        for item in r.json():
            PR = item['number']
            PRList.append(PR)
        return PRList
