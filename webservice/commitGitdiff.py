import os
import aiohttp
import asyncio
import json
import time
import datetime
import logging
import gidgethub
import requests
from gidgethub import aiohttp as gh_aiohttp
import pandas as pd
from utils.auth import get_jwt, get_installation, get_installation_access_token



class CommitGitDiff(object): 
    def __init__(self, user, repo, gh):
        self.pr_url = 'https://api.github.com/repos/%s/%s/pulls?per_page=100&page=1&q=addClass&state=all' %(user, repo)
        self.pr_files_url = 'https://api.github.com/repos/%s/%s/pulls/{}/files' %(user, repo)
        self.gh = gh
        self.user = user
        self.repo = repo
        self.commit_url = 'https://api.github.com/repos/%s/%s/pulls/{}/commits' %(user, repo)

    def getNextUrl(self, link):
        """遍历所有的PR"""
        next_str = None
        for i in link.split(','):
            if 'rel="next"' in i:
                next_str = i
                break
        if next_str != None:
            start_index = next_str.index('<')
            end_index = next_str.index('>')
            url = next_str[start_index+1:end_index]
        else:
            url = None
        return url

    async def getPRList(self):
        """
        1. 获取距离30天创建的PR列表:只获取，不做处理s
        return : []
        """
        today = datetime.date.today()
        month_Days_ago = str(today - datetime.timedelta(days=30))
        startTime = '2020-12-01'
        endTime = '2021-01-01'
        PRlist = [] 
        while (self.pr_url != None):
            print(self.pr_url)
            (code, header, body) = await self.gh._request("GET", self.pr_url, {'accept': 'application/vnd.github.antiope-preview+json'})
            res = json.loads(body.decode('utf8'))
            for item in res:
                if item['created_at'] > startTime and item['created_at'] < endTime:
                    PRlist.append(item['number'])
            print(res[-1]['number'])
            print(res[-1]['created_at'])
            if res[-1]['created_at'] < startTime:
                break
            else:
                self.pr_url = self.getNextUrl(header['link'])
        print(" %s - %s PRs: %s" %(startTime, endTime, PRlist))
        return overduelist


    async def PRFilesChanges(self):
        #PRlist = await self.getPRList()
        PRlist = [30056, 30055, 30054, 30053, 30052, 30051, 30050, 30049, 30047, 30046, 30045, 30044, 30042, 30041, 30040, 30038, 30037, 30036, 30035, 30034, 30033, 30032, 30031, 30028, 30027, 30025, 30024, 30023, 30022, 30020, 30019, 30017, 30016, 30015, 30014, 30013, 30011, 30010, 30009, 30008, 30007, 30006, 30004, 30003, 30002, 30001, 30000, 29999, 29998, 29997, 29996, 29995, 29994, 29993, 29992, 29991, 29989, 29988, 29987, 29986, 29984, 29983, 29982, 29981, 29980, 29979, 29977, 29975, 29974, 29973, 29972, 29971, 29970, 29969, 29968, 29967, 29966, 29965, 29964, 29963, 29962, 29961, 29960, 29958, 29957, 29956, 29955, 29954, 29953, 29952, 29950, 29949, 29948, 29947, 29946, 29945, 29943, 29942, 29941, 29940, 29939, 29938, 29937, 29936, 29934, 29933, 29932, 29931, 29930, 29929, 29928, 29927, 29926, 29925, 29924, 29923, 29921, 29918, 29917, 29916, 29915, 29914, 29913, 29911, 29909, 29907, 29906, 29905, 29904, 29903, 29902, 29901, 29900, 29898, 29897, 29896, 29894, 29893, 29892, 29891, 29890, 29889, 29888, 29885, 29883, 29882, 29881, 29880, 29879, 29878, 29876, 29874, 29873, 29872, 29869, 29867, 29866, 29862, 29861, 29859, 29858, 29856, 29855, 29853, 29851, 29842, 29840, 29837, 29836, 29834, 29832, 29830, 29828, 29826, 29824, 29822, 29821, 29820, 29819, 29818, 29817, 29816, 29815, 29814, 29813, 29810, 29809, 29807, 29806, 29805, 29804, 29803, 29801, 29800, 29799, 29798, 29797, 29796, 29795, 29792, 29790, 29789, 29788, 29786, 29785, 29784, 29782, 29781, 29778, 29777, 29776, 29775, 29774, 29772, 29771, 29770, 29769, 29767, 29766, 29765, 29764, 29758, 29757, 29756, 29755, 29753, 29750, 29748, 29747, 29746, 29745, 29744, 29741, 29740, 29739, 29738, 29736, 29735, 29734, 29733, 29732, 29731, 29730, 29729, 29728, 29727, 29726, 29725, 29724, 29723, 29721, 29720, 29719, 29718, 29717, 29715, 29714, 29713, 29712, 29711, 29708, 29707, 29706, 29705, 29704, 29702, 29701, 29698, 29697, 29695, 29694, 29692, 29672, 29671, 29670, 29668, 29666, 29665, 29663, 29662, 29659, 29658, 29657, 29656, 29655, 29640, 29633, 29628, 29627, 29626, 29624, 29623, 29622, 29621, 29620, 29618, 29617, 29616, 29615, 29614, 29613, 29612, 29611, 29607, 29606, 29605, 29604, 29603, 29602, 29601, 29600, 29599, 29598, 29597, 29595, 29594, 29593, 29590, 29589, 29588, 29587, 29586, 29583, 29582, 29581, 29580, 29579, 29578, 29577, 29576, 29575, 29574, 29572, 29571, 29570, 29569, 29568, 29567, 29566, 29565, 29564, 29563, 29562, 29561, 29560, 29559, 29556, 29553, 29552, 29551, 29550, 29549, 29548, 29547, 29545, 29544, 29543, 29541, 29540, 29539, 29538, 29537, 29535, 29532, 29531, 29529, 29528, 29527, 29526, 29525, 29523, 29522, 29521, 29519, 29518, 29517, 29516, 29515, 29514, 29512, 29511, 29509, 29508, 29505, 29504, 29503, 29502, 29501, 29500, 29499, 29498, 29496, 29495, 29494, 29493, 29492, 29491, 29490, 29489, 29488, 29486, 29485, 29484, 29480, 29479, 29478, 29477, 29476, 29475, 29474, 29473, 29470, 29469, 29468, 29467, 29466, 29465, 29464, 29463, 29462, 29461, 29460, 29459, 29458, 29457, 29455, 29451, 29449, 29448, 29447, 29446, 29445, 29443, 29442, 29441, 29440, 29437, 29436, 29435, 29434, 29433, 29432, 29431, 29430, 29429, 29427, 29426, 29425, 29424, 29423, 29422, 29421, 29420, 29419, 29418, 29417, 29416, 29414, 29413, 29412, 29411, 29410, 29408, 29407, 29406, 29405, 29404, 29397, 29394, 29393, 29392, 29391, 29390, 29388, 29387, 29386, 29384, 29383, 29382, 29381, 29380, 29378, 29377, 29376, 29375, 29374, 29373, 29372, 29371, 29370, 29369, 29368, 29367, 29366, 29365, 29364, 29363, 29361, 29360, 29359, 29358, 29357, 29356, 29355, 29354, 29352, 29351, 29350, 29349, 29348, 29347, 29346, 29344, 29343, 29342, 29341, 29340, 29339, 29338, 29337, 29336, 29333, 29332, 29331, 29330, 29329, 29327, 29326, 29325, 29324, 29323, 29322, 29321, 29319, 29318, 29317, 29316, 29315, 29313, 29312, 29311, 29310, 29309, 29308, 29307, 29306, 29305, 29304, 29303, 29302, 29301, 29300, 29299, 29297, 29295, 29294, 29293, 29292, 29291, 29290, 29289, 29288, 29285, 29284, 29283, 29282, 29281, 29280, 29279, 29278, 29277, 29276, 29275, 29274, 29273, 29272, 29271, 29270, 29269, 29268, 29267, 29266, 29265, 29264, 29263, 29262, 29261, 29260, 29259, 29257, 29255, 29254, 29253, 29252, 29248, 29247, 29246, 29238, 29236]
        PR_files_list = []
        for pr in PRlist:
            pr_file_dict = {}
            pr_files_url = self.pr_files_url.format(pr)
            headers = {'authorization': "token 6a11cc8c520f8793b7279b02b6c8d5dd6c1f5e05"}
            res = requests.get(pr_files_url, headers = headers).json()
            #(code, header, body) = await self.gh._request("GET", pr_files_url, {'accept': 'application/vnd.github.antiope-preview+json'})
            #res = json.loads(body.decode('utf8'))
            files = []
            for item in res:
                files.append(item['filename'])
            pr_file_dict[pr] = files
            print(pr_file_dict)
            PR_files_list.append(pr_file_dict)
        print(PR_files_list)

async def main(user, repo):
    async with aiohttp.ClientSession() as session:
        #app_id = os.getenv("GH_APP_ID")
        app_id = 59502
        jwt = get_jwt(app_id)
        gh = gh_aiohttp.GitHubAPI(session, user)
        try:
            installation = await get_installation(gh, jwt, user)
        except ValueError as ve:
            print(ve)
        else:
            access_token = await get_installation_access_token(
                gh, jwt=jwt, installation_id=installation["id"]
            )
            # treat access_token as if a personal access token
            gh = gh_aiohttp.GitHubAPI(session, user,
                        oauth_token=access_token["token"])
            commitObject = CommitGitDiff(user, repo, gh)
            await commitObject.PRFilesChanges()

loop = asyncio.get_event_loop()
loop.run_until_complete(main('PaddlePaddle', 'Paddle'))
