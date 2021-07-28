import json
import time
import sys
sys.path.append("..")
from utils.db import Database

class getExecTime(Database):
    def getALLCIDict(self):
        """
        this function will get all CIs. 
        Returns:
            repo_ci_dict(dict): {'repo': [ci_list]}.
        """
        with open("../conf/monitor.json", "r") as f:
            repo_ci_dict = json.load(f)
        return repo_ci_dict
        
    def getALLCIExecTime(self):
        """
        this function will get exectime of all CIs. 
        The format of the data saved in the file is `ciName_repo_ifDocument`.
        """
        execTime_dict = {}
        repo_ci_dict = self.getALLCIDict()
        for repo in repo_ci_dict:
            for ci in repo_ci_dict[repo]:
                print(ci)
                if repo in ['PaddlePaddle/Paddle']:
                    if ci == 'PR-CI-CPU-Py2':
                        for ifDocument in [True, False]:
                            key = '%s_%s_%s' %(ci, repo, ifDocument)
                            execTime_dict[key] = self.queryDBlastHour(ci, repo, ifDocument)
                    else:
                        key = '%s_%s_True' %(ci, repo)
                        execTime_dict[key] = 2 #The default time of document_fix cis is 2
                        key = '%s_%s_False' %(ci, repo)
                        execTime_dict[key] = self.queryDBlastHour(ci, repo, 'False')
                else:
                    ifDocument = False
                    key = '%s_%s_%s' %(ci, repo, ifDocument)
                    execTime_dict[key] = self.queryDBlastHour(ci, repo, ifDocument)
        if execTime_dict['xly-PR-CI-PY2_PaddlePaddle/Serving_False'] == None:
            execTime_dict['xly-PR-CI-PY2_PaddlePaddle/Serving_False'] = 30
        if execTime_dict['xly-PR-CI-PY3_PaddlePaddle/Serving_False'] == None:
            execTime_dict['xly-PR-CI-PY3_PaddlePaddle/Serving_False'] = 30
        if execTime_dict['PR-CI-CUDA9-CUDNN7_PaddlePaddle/Serving_False'] == None:
            execTime_dict['PR-CI-CUDA9-CUDNN7_PaddlePaddle/Serving_False'] = 30
        if execTime_dict['xly-PR-CI-PY27_PaddlePaddle/PaddleRec_False'] == None:
            execTime_dict['xly-PR-CI-PY27_PaddlePaddle/PaddleRec_False'] = 30
        if execTime_dict['xly-PR-CI-PY35_PaddlePaddle/PaddleRec_False'] == None:
            execTime_dict['xly-PR-CI-PY35_PaddlePaddle/PaddleRec_False'] = 30
        if execTime_dict['PaddleServing文档测试_PaddlePaddle/Serving_False'] == None:
            execTime_dict['PaddleServing文档测试_PaddlePaddle/Serving_False'] = 5
        if execTime_dict['xly-PR-CI-PY37_PaddlePaddle/FleetX_False'] == None:
            execTime_dict['xly-PR-CI-PY37_PaddlePaddle/FleetX_False'] = 30
        if execTime_dict['PR-CI-CPU-Py2_PaddlePaddle/Paddle_True'] == None:
            execTime_dict['PR-CI-CPU-Py2_PaddlePaddle/Paddle_True'] = execTime_dict['PR-CI-CPU-Py2_PaddlePaddle/Paddle_False']
        execTime_dict['xly-PR-CI-PY2_PaddlePaddle/PaddleRec_False'] = 30
        execTime_dict['xly-PR-CI-PY3_PaddlePaddle/PaddleRec_False'] = 30
        execTime_dict['build-paddle_PaddlePaddle/Paddle_False'] = 15
        execTime_dict['build-paddle_PaddlePaddle/Paddle_True'] = 15
        print(execTime_dict)
        with open("../buildLog/all_ci_execTime.json", "w") as f:
            json.dump(execTime_dict, f)
            f.close()

getExecTime().getALLCIExecTime()
