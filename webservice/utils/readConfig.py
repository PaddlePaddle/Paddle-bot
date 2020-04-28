import os
import codecs
import configparser

proDir = os.path.abspath(os.path.join(os.getcwd()))
configPath = os.path.join(proDir,"conf/config.ini")

class ReadConfig:
    def __init__(self):
        fd = open(configPath)
        data = fd.read()
        if data[:3] == codecs.BOM_UTF8:
            data = data[3:]
            file = codecs.open(configPath,'w')
            file.write(data)
            file.close()
        fd.close()
        self.cf = configparser.ConfigParser()
        self.cf.read(configPath, "utf-8")
