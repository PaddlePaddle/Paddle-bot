import requests
import json
import subprocess
import warnings

class handleIcafe(object):
    def __init__(self):
        instance = self.__getSetting__()
        self.configDict = instance
        self.infoUrl = instance['infoUrl']
        self.requestUrl = instance['url']
        self.utestUrl = instance['utestUrl']
        self.headers = instance['headers']
        self.username = instance['username']
        self.method = instance['method']
        self.context = instance['context']
        self.isSetContext = False

    def __getSetting__(self, place = 'icafe.json', mode = 'r'):
        with open(place, mode) as file:
            instance = file.read()
        return json.loads(instance)
    
    def saveUrl(self, place = 'icafe.txt', mode = 'a'):
        with open(place, mode) as file:
            file.write(self.url)
            file.write('\n')

    def raiseError(self, err):
        raise RuntimeError(
            (f"create requirements is error {err}")
        )

    def request(self):
        req = requests.Request(
            method = self.method, 
            url = self.requestUrl, 
            headers = self.headers, 
            data = self.context
        ).prepare()
        return requests.Session().send(req, timeout = 15).json()
    
    def handleDirector(self, res):
        if res['content'] == [] or res['content'][0]['st_user'] == '':
            self.holder = self.configDict["defaultDirector"]
        else:
            self.holder = res['content'][0]['st_user']

    def getDirectorEmail(self):
        url = self.infoUrl + self.holder
        req = requests.Request(
            method = "GET", 
            url = url,
            headers = self.headers
        ).prepare()
        self.holderEmail = requests.Session().send(req, timeout = 15).json()[0]['email']
        return  self.holderEmail

    def getDirector(self, utest):
        url = self.utestUrl + utest
        req = requests.Request(
            method = "GET", 
            url = url,
            headers = self.headers
        ).prepare()
        res = requests.Session().send(req, timeout = 15).json()
        self.handleDirector(res)
        self.setHolder()
        self.getDirectorEmail()
        return self.holder

    def setHolder(self):
        self.context['issues'][0]['fields']["负责人"] = "刘娇蒂"
        self.context = json.dumps(self.context)

    def getSendCmd(self, name):
            url = self.configDict["sendToGroupUrl"]
            content = "' " + json.dumps(self.configDict[name])
            header = self.configDict['sendToGroupHeader']
            cmd = "curl -X POST "+ url + " -H " + header + " -d "
            return cmd, content

    def setContent(self, ctx):
        template = self.configDict["contentTemplate"]
        context = ""
        for item in ctx:
            context += ("<br/>" +template.format(
                item[0], item[1],
                item[2], item[3]
            ))
        self.isSetContext = True
        self.context['issues'][0]["detail"] += context

    def checkIsSetValue(self):
        if self.isSetContext == False:
            warnings.warn("icafe detail has't set")
        
    def create(self, utest):
        self.checkIsSetValue()
        self.getDirector(utest)
        try:
            res = self.request()
            failures = res.get("failures")
        except Exception as e:
            self.raiseError(e)
        if res.get("status") != 200:
            self.raiseError(failures)

        self.setAttribute(res["issues"][0])
        self.saveUrl()
        self.context = self.configDict['context']
        return True

    def setAttribute(self, res):
        self.url = res['url']
        self.issueId = res['issueId']
        self.sequence = res["sequence"]
    
    def parsePacket(self, nowUtest, packet, ctx, users):
        if packet != []:
            self.setContent(packet)
            self.create(nowUtest)
            users += ("\"" + self.holderEmail + "\"" + ",")
            ctx += (nowUtest + ' @' + self.holder + ' ' + self.url + "\\n")

    def subprocessAt(self, users):
        users = users[:-1]
        cmd, content = self.getSendCmd("sendToGroupAt")
        pos = content.find("atuserids") + len("atuserids") + 3
        content = content[:pos + 1] + users + content[pos + 1:]
        content += " '"
        cmd += content
        subprocess.run(cmd, shell = True)

    def subprocessContent(self, ctx):
        cmd, content = self.getSendCmd("sendToGroupAll")
        content = content%(ctx)
        content += " '"
        cmd += content
        subprocess.run(cmd, shell = True)

    def sendToGroup(self, datas):
        ctx = "\\n"
        nowUtest = ''
        packet = []
        size = len(datas)
        idx = 1
        users = ""
        for item in datas:
            utest = item[0]
            if nowUtest != utest or idx >= size:
                self.parsePacket(nowUtest, packet, ctx, users)
                packet.clear()
                nowUtest = utest
            packet.append(item)
            idx += 1
        self.subprocessContent(ctx)
        self.subprocessAt(users)
        
