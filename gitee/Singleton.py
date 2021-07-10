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
    def __init__(self, pr):
        self.type = 'PR'
        self.pr_no_ = pr
        self.migrate_state = 'failed'
        self.merge_state = '未合入'

    def set_migrate_state(self, state):
        self.migrate_state = state

    def set_merge_state(self, state):
        self.merge_state = state

    def to_arr(self):
        return [ self.type, self.pr_no_, self.migrate_state, self.merge_state ]

@singleton
class MySingleton(object):
    def __init__(self):
        self.total_pr_state = defaultdict(list)
    
    def new_pr(self, pr):
        self.total_pr_state[ pr ] = PRState( pr )

    def set_pr_migrate_state(self, pr, state):
        assert self.total_pr_state.get(pr) != None
        pr_state = self.total_pr_state.get( pr )
        pr_state.set_migrate_state( state )

    def set_pr_merge_state(self, pr, state):
        assert self.total_pr_state.get(pr) != None
        pr_state = self.total_pr_state.get( pr )
        pr_state.set_merge_state( state )

    def to_html(self, title='PR迁移状态表格'):
        arr_ = self.to_2d_arr()
        table = pd.DataFrame( arr_, columns=['类型', 'PR号', '迁移状态', 'merge状态'] )
        ret = table.to_html( index=False,justify='center' )
        ret = ret.replace('class="dataframe">',
                                        'class="dataframe"><caption>{}</caption>'.format(title)
                                        )   
        ret = ret.replace('<table', '<table align="center"')
        return ret 
    
    def to_2d_arr(self):
        ret = []
        for k, v in self.total_pr_state.items():
            ret.append( v.to_arr() )
        return ret

