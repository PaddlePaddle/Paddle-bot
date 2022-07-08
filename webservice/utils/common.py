import time
import datetime


class CommonModule(object):
    def utcTimeToStrTime(self, utcTime):
        """utc时间转换为当地时间"""
        UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        utcTime = datetime.datetime.strptime(utcTime, UTC_FORMAT)
        localtime = utcTime + datetime.timedelta(hours=8)
        return localtime

    def strTimeToTimestamp(self, strTime):
        """字符串时间转换为时间戳"""
        time_array = time.strptime(strTime, '%Y-%m-%d %H:%M:%S')
        timeStamp = int(time.mktime(time_array))
        return timeStamp

    def TimestampTostrTime(self, timeStamp):
        """时间戳转换为当地时间"""
        time_local = time.localtime(timeStamp)
        localtime = time.strftime('%Y-%m-%d %H:%M:%S', time_local)
        return localtime
