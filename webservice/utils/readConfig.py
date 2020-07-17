import os
import codecs
import configparser

proDir = os.path.abspath(os.path.join(os.getcwd()))


class ReadConfig:
    def __init__(self, path="conf/config.ini"):
        configPath = os.path.join(proDir, path)
        fd = open(configPath)
        data = fd.read()
        if data[:3] == codecs.BOM_UTF8:
            data = data[3:]
            file = codecs.open(configPath, 'w')
            file.write(data)
            file.close()
        fd.close()
        self.cf = configparser.ConfigParser()
        self.cf.read(configPath, "utf-8")
