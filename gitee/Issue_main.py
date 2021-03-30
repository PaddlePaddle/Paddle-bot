import GithubLabelToGitee
import GithubToGitee

github_header = {
    'User-Agent': 'Mozilla/5.0',
    'Authorization': '',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
create_token = ""
close_token = ""
repo_list = ['']

for repo in repo_list:
    label_app = GithubLabelToGitee.GithubLabelToGitee(repo, github_header,
                                                      close_token)
    label_app.CreateGiteeLabel()
    issue_app = GithubToGitee.GithubIssueToGitee(repo, github_header,
                                                 create_token)
    issue_app.CreateIssueToGitee(close_token)
