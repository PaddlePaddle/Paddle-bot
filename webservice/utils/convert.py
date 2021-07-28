import time
import datetime

def javaTimeTotimeStamp(commitTime):
    commitTime = commitTime.replace('T', ' ').replace('Z', '') #java time To string
    commitTime = time.strptime(commitTime, '%Y-%m-%d %H:%M:%S')
    dt = datetime.datetime.fromtimestamp(time.mktime(commitTime))
    actualCreateTime = (dt + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    timeArray = time.strptime(actualCreateTime, "%Y-%m-%d %H:%M:%S")
    createTime = int(time.mktime(timeArray))
    return createTime

def strTimeTotimeStamp(strTime):
    time_array = time.strptime(strTime, '%Y-%m-%d %H:%M:%S')
    timeStamp = int(time.mktime(time_array))
    return timeStamp