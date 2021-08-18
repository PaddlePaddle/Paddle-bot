#~/usr/bin/python3

# 1. 根据log找到对应的excode: 
#    首先根据关键字比如conection refused匹配到就是503，
#    如果没有匹配则根据excode去匹配，
#    如果excode也没有匹配则是Unknown Failed
# 2. 根据excode去字典找到describe
# 3. 每个excode都有一个对应的关键字，全部都找到然后对一下
# 4. 根据关键字去截取log


class LogProcessMap(object):
    def __init__(self, excode_dict):
        self.cutterFunc = {
            '64': self.TestFailedCutter,
            '63': self.TestFailedCutter,
            '65': self.TestFailedCutter,
            '7': self.TestFailedCutter,
            '8': self.TestFailedCutter,
            '9': self.TestFailedCutter,
            '503': self.TestFailedCutter,
            '6': self.TestFailedCutter,
            '4': self.TestFailedCutter,
            '2': self.TestFailedCutter,
            '15': self.TestFailedCutter
        }

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
        key_word = self.excode2keyword[excode]
        key_word_index = self.find_key_word_index(log_arr, key_word)
        return self.DefaultCut(log_arr, key_word_index)

    def DefaultCut(self, log_arr, index):
        left = max(0, index - 10)
        right = min(len(log_arr), index + 11)
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
        for i in range(log_length - 1, -1, -1):
            if log_arr[i].find(key_word) != -1:
                index = i
                break
        return index

    def run(self, excode, log):
        describe = self.excode2name[
            excode] if excode in self.excode2name else "Unknown Failed"
        if excode not in self.cutterFunc:
            return describe, self.DefaultCutter(excode, log)
        return describe, self.cutterFunc[excode](excode, log)


# if __name__ == '__main__':
#     go = LogProcessMap()
#     go.run( '1', None )
