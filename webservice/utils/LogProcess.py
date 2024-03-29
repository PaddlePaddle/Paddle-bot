#!/usr/bin/python3

# 1. 根据log找到对应的excode: 
#    首先根据关键字比如conection refused匹配到就是503，
#    如果没有匹配则根据excode去匹配，
#    如果excode也没有匹配则是Unknown Failed
# 2. 根据excode去字典找到describe
# 3. 每个excode都有一个对应的关键字，全部都找到然后对一下
# 4. 根据关键字去截取log


class LogProcessMap(object):
    def __init__(self, excode_dict):
        # TODO: 为相应错误码设置对应的回调函数
        self.cutterFunc = {
            '64': self.CenterCutter,
            '63': self.CenterCutter,
            '65': self.CenterCutter,
            '7': self.CenterCutter,
            '8': self.TestFailedCutter,
            '9': self.CenterCutter,
            '503': self.CenterCutter,
            '6': self.CenterCutter,
            '4': self.CenterCutter,
            '2': self.CenterCutter,
            '15': self.CenterCutter
        }

        # TODO: 配置错误码对应的关键字
        self.excode2keyword = {
            '64': 'check docker md5 fail',
            '63': '',
            '65': '',
            '7': 'Build Paddle failed, will exit',
            '8': 'The following tests FAILED',
            '9': 'Coverage Failed',
            '503': 'Failed to connect to',
            '6': 'approved error',
            '4': 'Code format error',
            '2': 'Automatic merge failed',
            '15': 'refusing to merge unrelated histories',
        }

        self.excode2name = {}
        for k, v in excode_dict.items():
            self.excode2name[str(v)] = k

    def TestFailedCutter(self, excode, log_arr):
        if excode not in self.excode2keyword:
            return self.DefaultCutter(excode, log_arr)
        # 找到excode对应的关键字
        key_word = self.excode2keyword[excode]
        # 找到关键字那一行所在的下标
        key_word_index, find = self.find_key_word_index(log_arr, key_word)
        if not find:
            return self.DefaultCutter(excode, log_arr)
        return self.RangeCut(log_arr, key_word_index, 0, 21)

    def CenterCutter(self, excode, log_arr):
        if excode not in self.excode2keyword:
            return self.DefaultCutter(excode, log_arr)
        # 找到excode对应的关键字
        key_word = self.excode2keyword[excode]
        # 找到关键字那一行所在的下标
        key_word_index, find = self.find_key_word_index(log_arr, key_word)
        if not find:
            return self.DefaultCutter(excode, log_arr)
        return self.DefaultCut(log_arr, key_word_index)

    # 以index所在行为中心，截取前10行和后10行
    def DefaultCut(self, log_arr, index):
        return self.RangeCut(log_arr, index, -10, 11)

    def RangeCut(self, log_arr, index, upper_bias, lower_bias):
        length = len(log_arr)
        left = min(length, max(0, index + upper_bias))
        right = min(length, max(0, index + lower_bias))
        print('cut[%d, %d]' % (left, right))
        return ''.join(log_arr[left:right])

    def DefaultCutter(self, excode, log_arr):
        if log_arr == None:
            return None
        length = len(log_arr)
        left = max(0, length - 20)
        right = length
        ret = log_arr[left:right]
        ret = ''.join(ret)
        return ret

    def find_key_word_index(self, log_arr, key_word):
        log_length = len(log_arr)
        # 防止越界
        index = max(0, log_length - 1)
        find = False
        for i in range(log_length - 1, -1, -1):
            if log_arr[i].find(key_word) != -1:
                index = i
                find = True
                break
        return index, find

    # 这里的log_arr是日志内容字符串按行分割的数组，每个元素是日志的一行
    def run(self, excode, log_arr):
        # 找到excode对应的描述信息，如果是未知excode，则赋值为Unknown
        describe = self.excode2name[
            excode] if excode in self.excode2name else "Unknown Failed"
        # 如果excode是未知的，则默认截取最后20行
        if excode not in self.cutterFunc:
            return describe, self.DefaultCutter(excode, log_arr)
        # 否则回调相应的函数
        return describe, self.cutterFunc[excode](excode, log_arr)
