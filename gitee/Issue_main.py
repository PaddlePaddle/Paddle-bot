import GithubLabelToGitee
import GithubToGitee


github_header = {'User-Agent': 'Mozilla/5.0',
            'Authorization': 'token 6da68be1531f915bd096caffeea235b7a66bee4c',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            }
create_token = "04388373ac19b581f4d2e8238131b20a"
close_token = "2cdf216aec161faf951dbb7d51279e07"
repo_list = ['paddlepaddle/Paddle']


for repo in repo_list:
    label_app = GithubLabelToGitee.GithubLabelToGitee(repo, github_header, close_token)
    label_app.CreateGiteeLabel()
    issue_app = GithubToGitee.GithubIssueToGitee(repo, github_header, create_token)
    issue_app.CreateIssueToGitee(close_token)
