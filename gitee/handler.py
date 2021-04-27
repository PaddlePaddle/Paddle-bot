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
