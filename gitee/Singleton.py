# encoding:utf-8
from collections import defaultdict
import pandas as pd


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


class PRState(object):
    def __init__(self, github_pr_):
        self.type = 'PR'
        self.github_pr = github_pr_
        self.gitee_pr = -1
        self.migrate_state = 'failed'
        self.merge_state = '未合入'

    def set_migrate_state(self, state):
        self.migrate_state = state

    def set_merge_state(self, state):
        self.merge_state = state

    def set_gitee_pr(self, gitee_pr_):
        self.gitee_pr = gitee_pr_

    def to_arr(self):
        return [
            self.type, self.github_pr, self.migrate_state, self.merge_state
        ]


@singleton
class MySingleton(object):
    def __init__(self):
        self.total_pr_state = defaultdict(list)
        self.gitee_pr_to_github_pr = defaultdict(list)

    def new_pr(self, pr):
        assert self.total_pr_state.get(pr) == None
        self.total_pr_state[pr] = PRState(pr)

    def set_pr_migrate_state(self, pr, state):
        assert self.total_pr_state.get(pr) != None
        pr_state = self.total_pr_state.get(pr)
        pr_state.set_migrate_state(state)

    def set_pr_merge_state(self, pr, state):
        assert self.total_pr_state.get(pr) != None
        pr_state = self.total_pr_state.get(pr)
        pr_state.set_merge_state(state)

    def to_html(self, title='PR迁移状态表格'):
        table = self.to_2d_arr()
        table = pd.DataFrame(table, columns=['类型', 'PR号', '迁移状态', 'merge状态'])
        ret = table.to_html(index=False, justify='center')
        ret = ret.replace(
            'class="dataframe">',
            'class="dataframe"><caption>{}</caption>'.format(title))
        ret = ret.replace('<table', '<table align="center"')
        return ret

    def add(self, pr_state):
        assert self.total_pr_state.get(pr_state.github_pr) == None
        self.total_pr_state[pr_state.github_pr] = pr_state
        if pr_state.gitee_pr != -1:
            self.gitee_pr_to_github_pr[pr_state.gitee_pr] = pr_state

    def get_github_pr_by_gitee_pr(self, gitee_pr):
        assert self.gitee_pr_to_github_pr.get(gitee_pr) != None
        return self.gitee_pr_to_github_pr[gitee_pr]

    def to_2d_arr(self):
        ret = []
        for k, v in self.total_pr_state.items():
            ret.append(v.to_arr())
        return ret

    def is_empty(self):
        return False if len(self.total_pr_state) != 0 else True
