from utils.readConfig import ReadConfig
from utils.mail import Mail
from utils.db import Database
import datetime
import xlwt
import pandas as pd
import codecs
from utils.mail import Mail

localConfig = ReadConfig()

def queryCIDataWeekly(lastWeek):
    time_monitor_list = localConfig.cf.get('ciIndex', 'time_monitor').split(',') 
    other_monitor_list = localConfig.cf.get('ciIndex', 'other_monitor').split(',') 
    ci_index = {}
    noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where time > '%s'" % lastWeek
    noRepeat_commitCount = queryDB(noRepeat_commitCount_query_stat, 'count')
    ci_index['commitCount'] = noRepeat_commitCount
    for ci in ['PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2']:
        average_exec_time_query_stat = "select mean(t)/60 from (select endTime-startTime as t from paddle_ci_index where ciName='%s' and time > '%s')" % (ci, lastWeek)
        average_exec_time = queryDB(average_exec_time_query_stat, 'mean')
        key = '%s_average_exec_time' %ci
        ci_index[key] = "%.2f" % average_exec_time
        for param in time_monitor_list:
            average_value = queryStatMean(param, ci, lastWeek)
            key = '%s_%s' %(ci, param)
            ci_index[key] = "%.2f" % average_value if average_value != None else None
        for param in other_monitor_list:
            average_value = queryStatMean(param, ci, lastWeek, form='size')
            key = '%s_%s' %(ci, param)
            ci_index[key] = "%.2f" % average_value if average_value != None else None
        noRepeat_commitCount_query_stat = "SELECT COUNT(distinct commitId) from paddle_ci_status where ciName='%s' and time > '%s'" % (ci, lastWeek)
        noRepeat_commitCount = queryDB(noRepeat_commitCount_query_stat, 'count')  
        all_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName='%s' and time > '%s'" % (ci, lastWeek)
        all_commitCount = queryDB(all_commitCount_query_stat, 'count')
        key = "%s_rerunRate" %ci
        ci_index[key] = "%.2f" %(1 - noRepeat_commitCount/all_commitCount)
        fail_commitCount_query_stat = "SELECT COUNT(commitId) from paddle_ci_status where ciName='%s' and status='failure' and time > '%s'" % (ci, lastWeek)
        fail_commitCount = queryDB(fail_commitCount_query_stat, 'count')
        key = "%s_failRate" %ci
        ci_index[key] = "%.2f" %(fail_commitCount/all_commitCount)
    return ci_index
    
def queryStatMean(index, ci, queryTime, form='time'):
    if form == 'size':
        query_stat = "select mean(%s) from paddle_ci_index where ciName='%s' and time > '%s'" % (index, ci, queryTime)
    else:
        query_stat = "select mean(%s)/60 from paddle_ci_index where ciName='%s' and time > '%s'" % (index, ci, queryTime)
    result = queryDB(query_stat, 'mean')
    return result

def queryDB(query_stat, mode):
    db = Database()
    result = list(db.query(query_stat))
    if len(result) == 0:
        count = None
    else:
        count = result[0][0][mode]
    return count

def keyIndicators(ci_index):
    key_ci_index = {}
    xly_average_exec_time = float(0)
    xly_average_buildTime = float(0)
    xly_average_testCaseTime_total = float(0)
    xly_average_rerunRate = float(0)
    xly_average_failRate = float(0)
    for ci in ['PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2']:
        key = '%s_average_exec_time' %ci
        xly_average_exec_time = xly_average_exec_time + float(ci_index[key])
        key = '%s_buildTime' %ci
        xly_average_buildTime = xly_average_buildTime + float(ci_index[key])
        key = '%s_testCaseTime_total' %ci
        if ci_index[key] == None:
            ci_index[key] = 0
        xly_average_testCaseTime_total = xly_average_testCaseTime_total + float(ci_index[key])
        key = '%s_rerunRate' %ci
        xly_average_rerunRate = xly_average_rerunRate + float(ci_index[key])
        key = '%s_failRate' %ci
        xly_average_failRate = xly_average_failRate + float(ci_index[key])
    key_ci_index['xly_average_exec_time'] = "%.2f" % xly_average_exec_time
    key_ci_index['xly_buildTime'] = "%.2f" % xly_average_buildTime
    key_ci_index['xly_testCaseTime_total'] = "%.2f" % xly_average_testCaseTime_total
    key_ci_index['xly_rerunRate'] = "%.2f" % (xly_average_rerunRate / 4)
    key_ci_index['xly_failRate'] = "%.2f" % (xly_average_failRate / 4)
    return key_ci_index

def sheet_color(color):
    """set color and set center"""
    #0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray
    color_dic = {"Black":0, "White": 1, "Red": 2, "Green": 3, "Blue": 4, "Yellow": 5, "Gray": 22}
    style = xlwt.XFStyle() 
    pattern = xlwt.Pattern()
    alignment = xlwt.Alignment() 
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    style.alignment = alignment
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
    pattern.pattern_fore_colour = color_dic[color]
    style.pattern = pattern 
    return style

def set_center():
    """set center"""
    style = xlwt.XFStyle()
    alignment = xlwt.Alignment() 
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    style.alignment = alignment
    return style

def write_excel_xls(ciIndex_thisWeek, ciIndex_lastWeek):
    key_ci_index_thisWeek = keyIndicators(ciIndex_thisWeek)
    key_ci_index_lastWeek = keyIndicators(ciIndex_lastWeek)
    today = datetime.date.today()
    thisWeek = str(today - datetime.timedelta(days=7))
    workbook = xlwt.Workbook(encoding = 'utf-8')
    worksheet = workbook.add_sheet('%s~%s' %(thisWeek, today))
    worksheet.col(0).width = 6666
    worksheet.write(0, 0, "效率云%s~%s CI关键指标" %(thisWeek, today), sheet_color("Yellow"))
    worksheet.write(1, 0, "指标", sheet_color("Gray"))
    worksheet.write(1, 1, "本周值", sheet_color("Gray"))
    worksheet.write(1, 2, "上周值", sheet_color("Gray"))
    worksheet.write(1, 3, "变化", sheet_color("Gray"))
    key_ci_index_dic = {"平均执行时间/min": "xly_average_exec_time", "平均编译时间/min": "xly_buildTime", "平均单测时间/min": "xly_testCaseTime_total", "平均rerun率": "xly_rerunRate", "平均失败率": "xly_failRate"} 
    line = 2
    for i in ['平均执行时间/min', '平均编译时间/min', '平均单测时间/min', '平均rerun率', '平均失败率']:    
        worksheet.write(line, 0, i, set_center())
        worksheet.write(line, 1, key_ci_index_thisWeek[key_ci_index_dic[i]], set_center())
        worksheet.write(line, 2, key_ci_index_lastWeek[key_ci_index_dic[i]], set_center())
        sub_thisWeek_lastWeek_value = float(key_ci_index_thisWeek[key_ci_index_dic[i]]) - float(key_ci_index_lastWeek[key_ci_index_dic[i]])
        if sub_thisWeek_lastWeek_value > 0:
            worksheet.write(line, 3, '↑ %.2f' %sub_thisWeek_lastWeek_value, sheet_color("Red"))
        else:
            worksheet.write(line, 3, '↓ %.2f' %abs(sub_thisWeek_lastWeek_value), set_center())
        line = line + 1
    worksheet.write(8, 0, "效率云各CI关键指标", sheet_color("Yellow"))
    worksheet.write(9, 0, "指标", sheet_color("Gray"))
    worksheet.write(9, 1, "CI名称", sheet_color("Gray"))
    worksheet.write(9, 2, "本周值", sheet_color("Gray"))
    worksheet.write(9, 3, "上周值", sheet_color("Gray"))
    worksheet.write(9, 4, "变化", sheet_color("Gray"))
    line = 10
    for i in ['平均执行时间/min', '平均编译时间/min', '平均单测时间/min', '平均rerun率', '平均失败率']:
        worksheet.write(line, 0, i, set_center())
        for ci_name in ['PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2']:
            worksheet.write(line, 1, ci_name, set_center())
            key = key_ci_index_dic[i].replace('xly', ci_name)
            worksheet.write(line, 2, ciIndex_thisWeek[key], set_center())
            worksheet.write(line, 3, ciIndex_lastWeek[key], set_center())
            sub_thisWeek_lastWeek_value = float(ciIndex_thisWeek[key]) - float(ciIndex_lastWeek[key])
            if sub_thisWeek_lastWeek_value > 0:
                worksheet.write(line, 4, '↑ %.2f' %sub_thisWeek_lastWeek_value, sheet_color("Red"))
            else:
                worksheet.write(line, 4, '↓ %.2f' %abs(sub_thisWeek_lastWeek_value), set_center())
            line = line + 1

    ci_index_dic = {"00平均执行时间/min": "ci_average_exec_time", "01平均编译时间/min": "ci_buildTime", "02平均单测时间/min": "ci_testCaseTime_total", "03平均测试预测库时间/min": "ci_testFluidLibTime", \
        "04平均测试训练库时间/min": "ci_testFluidLibTrainTime", "05平均预测库大小/M": "ci_fluidInferenceSize", "06平均whl大小/M": "ci_WhlSize", \
        "07平均build目录大小/G": "ci_buildSize", "08单测总数/个": "ci_testCaseCount_total", "09单卡case总数/个": "ci_testCaseCount_single", \
        "10单卡case执行时间/min": "ci_testCaseTime_single", "11多卡case总数/个": "ci_testCaseCount_multi", "12多卡case执行时间/min": "ci_testCaseTime_multi", \
        "13独占case总数/个": "ci_testCaseCount_exclusive", "14独占case执行时间/min": "ci_testCaseTime_exclusive", "15平均失败率": "ci_failRate", \
        "16平均rerun率": "ci_rerunRate"}
    worksheet.write(31, 0, "效率云各CI本周的详细指标", sheet_color("Yellow"))
    worksheet.write(32, 0, "CI名称", sheet_color("Gray"))
    ci_index_key_list = sorted(ci_index_dic.keys())
    for i in range(len(ci_index_dic)):
        worksheet.col(i+1).width = 4444
        key = ci_index_key_list[i][2:]
        worksheet.write(32, i+1, key, sheet_color("Gray"))
    line = 33
    for ci_name in ['PR-CI-Py35', 'PR-CI-Coverage', 'PR-CI-Inference', 'PR-CI-CPU-Py2']:
        worksheet.write(line, 0, ci_name, set_center())
        for i in range(len(ci_index_dic)):
            key = ci_index_key_list[i]
            index = ci_index_dic[key].replace('ci', ci_name)
            if ciIndex_thisWeek[index] == 0 or ciIndex_thisWeek[index] == None:
                value = "None"
            else:
                value = ciIndex_thisWeek[index]
            worksheet.write(line, i+1, value, set_center())
        line = line +1
    workbook.save('ci_index%s.xls' %str(today))
    '''


def generateHtml1(key_ci_index_thisWeek, key_ci_index_lastWeek):
    sub_ = float(key_ci_index_thisWeek[key_ci_index_dic[i]]) - float(key_ci_index_lastWeek[key_ci_index_dic[i]])
    html = """
    <html>  
    <head></head>  
    <body>  
        <p><strong>效率云%s~%s CI关键指标</strong></p>
        <div id="content">
        <table width="500">
        <tr>
            <td bgcolor="gary"><strong>指标</strong></td>
            <td bgcolor="gary"><strong>本周值</strong></td>
            <td bgcolor="gary"><strong>上周值</strong></td>
            <td bgcolor="gary"><strong>变化</strong></td>
        </tr>
        <tr>
            <td>平均执行时间/min</td>
            <td>""" + key_ci_index_thisWeek['xly_average_exec_time'] + """</td>
            <td>""" + key_ci_index_lastWeek['xly_average_exec_time'] + """</td>
            <td>""" + key_ci_index_thisWeek['xly_average_exec_time'] + """</td>
        </tr>
        <tr>
            <td>平均编译时间/min</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        <tr>
            <td>平均单测时间/min</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        <tr>
            <td>平均rerun率</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        <tr>
            <td>平均失败率</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
    </body>  
    </html>  
    """
'''
def generateHtml():
    today = datetime.date.today()
    thisWeek = str(today - datetime.timedelta(days=7))
    xd = pd.ExcelFile('ci_index%s.xls' %str(today))
    df = xd.parse()
    with codecs.open('ci_index%s.html' %str(today),'w','utf-8') as html_file:
        html_file.write(df.to_html(header = True,index = False))
    f = open('ci_index%s.html' %str(today), 'rb') 
    mail_body = f.read()
    f.close()
    mail = Mail()
    mail.set_sender('zhangchunle@baidu.com')
    mail.set_receivers(['zhangchunle@baidu.com'])
    mail.set_title('效率云%s~%s CI评价指标统计' %(thisWeek, today))
    mail.set_message(mail_body, messageType='html')
    mail.send()

def send_excel(thisWeek, today):
    mail = Mail()
    mail.set_sender('zhangchunle@baidu.com')
    mail.set_receivers(['zhangchunle@baidu.com', 'luotao02@baidu.com'])
    mail.set_title('效率云%s~%s CI评价指标统计' %(thisWeek, today))
    sendfile = open('ci_index%s.xls' %str(today), 'rb').read()

    mail.set_message(sendfile, messageType='base64', encoding='utf-8')
    mail.body["Content-Type"] = 'application/octet-stream'
    mail.body["Content-Disposition"] = 'attachment; filename="ci_index%s.xls"' %str(today)
    mail.send()

def main():
    
    today = datetime.date.today()
    thisWeek = str(today - datetime.timedelta(days=7))
    lastWeek = str(today - datetime.timedelta(days=14))
    '''
    ciIndex_thisWeek = queryCIDataWeekly(thisWeek)
    ciIndex_lastWeek = queryCIDataWeekly(lastWeek)
    '''
    ciIndex_thisWeek = {'commitCount': 498, 'PR-CI-Py35_average_exec_time': '50.81', 'PR-CI-Py35_buildTime': '9.47', 'PR-CI-Py35_testFluidLibTime': None, 'PR-CI-Py35_testFluidLibTrainTime': None, 'PR-CI-Py35_testCaseTime_total': '32.81', 'PR-CI-Py35_testCaseTime_single': '20.73', 'PR-CI-Py35_testCaseTime_multi': None, 'PR-CI-Py35_testCaseTime_exclusive': '10.06', 'PR-CI-Py35_fluidInferenceSize': None, 'PR-CI-Py35_WhlSize': '79.00', 'PR-CI-Py35_buildSize': '9.60', 'PR-CI-Py35_testCaseCount_total': '978.45', 'PR-CI-Py35_testCaseCount_single': '907.58', 'PR-CI-Py35_testCaseCount_multi': None, 'PR-CI-Py35_testCaseCount_exclusive': '41.02', 'PR-CI-Py35_rerunRate': '0.55', 'PR-CI-Py35_failRate': '0.82', 'PR-CI-Coverage_average_exec_time': '118.97', 'PR-CI-Coverage_buildTime': '32.76', 'PR-CI-Coverage_testFluidLibTime': None, 'PR-CI-Coverage_testFluidLibTrainTime': None, 'PR-CI-Coverage_testCaseTime_total': '73.67', 'PR-CI-Coverage_testCaseTime_single': '54.00', 'PR-CI-Coverage_testCaseTime_multi': None, 'PR-CI-Coverage_testCaseTime_exclusive': '12.60', 'PR-CI-Coverage_fluidInferenceSize': None, 'PR-CI-Coverage_WhlSize': '828.59', 'PR-CI-Coverage_buildSize': '54.00', 'PR-CI-Coverage_testCaseCount_total': '1067.16', 'PR-CI-Coverage_testCaseCount_single': '993.41', 'PR-CI-Coverage_testCaseCount_multi': None, 'PR-CI-Coverage_testCaseCount_exclusive': '43.00', 'PR-CI-Coverage_rerunRate': '0.54', 'PR-CI-Coverage_failRate': '0.84', 'PR-CI-Inference_average_exec_time': '14.62', 'PR-CI-Inference_buildTime': '4.82', 'PR-CI-Inference_testFluidLibTime': '1.71', 'PR-CI-Inference_testFluidLibTrainTime': '0.26', 'PR-CI-Inference_testCaseTime_total': None, 'PR-CI-Inference_testCaseTime_single': None, 'PR-CI-Inference_testCaseTime_multi': None, 'PR-CI-Inference_testCaseTime_exclusive': None, 'PR-CI-Inference_fluidInferenceSize': '203.09', 'PR-CI-Inference_WhlSize': None, 'PR-CI-Inference_buildSize': None, 'PR-CI-Inference_testCaseCount_total': None, 'PR-CI-Inference_testCaseCount_single': None, 'PR-CI-Inference_testCaseCount_multi': None, 'PR-CI-Inference_testCaseCount_exclusive': None, 'PR-CI-Inference_rerunRate': '0.50', 'PR-CI-Inference_failRate': '0.63', 'PR-CI-CPU-Py2_average_exec_time': '19.08', 'PR-CI-CPU-Py2_buildTime': '2.64', 'PR-CI-CPU-Py2_testFluidLibTime': None, 'PR-CI-CPU-Py2_testFluidLibTrainTime': None, 'PR-CI-CPU-Py2_testCaseTime_total': None, 'PR-CI-CPU-Py2_testCaseTime_single': None, 'PR-CI-CPU-Py2_testCaseTime_multi': None, 'PR-CI-CPU-Py2_testCaseTime_exclusive': None, 'PR-CI-CPU-Py2_fluidInferenceSize': None, 'PR-CI-CPU-Py2_WhlSize': '89.00', 'PR-CI-CPU-Py2_buildSize': '5.80', 'PR-CI-CPU-Py2_testCaseCount_total': None, 'PR-CI-CPU-Py2_testCaseCount_single': None, 'PR-CI-CPU-Py2_testCaseCount_multi': None, 'PR-CI-CPU-Py2_testCaseCount_exclusive': None, 'PR-CI-CPU-Py2_rerunRate': '0.50', 'PR-CI-CPU-Py2_failRate': '0.84'}
    ciIndex_lastWeek = {'commitCount': 618, 'PR-CI-Py35_average_exec_time': '52.55', 'PR-CI-Py35_buildTime': '9.39', 'PR-CI-Py35_testFluidLibTime': None, 'PR-CI-Py35_testFluidLibTrainTime': None, 'PR-CI-Py35_testCaseTime_total': '33.92', 'PR-CI-Py35_testCaseTime_single': '20.69', 'PR-CI-Py35_testCaseTime_multi': None, 'PR-CI-Py35_testCaseTime_exclusive': '10.80', 'PR-CI-Py35_fluidInferenceSize': None, 'PR-CI-Py35_WhlSize': '79.01', 'PR-CI-Py35_buildSize': '9.60', 'PR-CI-Py35_testCaseCount_total': '977.42', 'PR-CI-Py35_testCaseCount_single': '906.73', 'PR-CI-Py35_testCaseCount_multi': None, 'PR-CI-Py35_testCaseCount_exclusive': '41.01', 'PR-CI-Py35_rerunRate': '0.55', 'PR-CI-Py35_failRate': '0.82', 'PR-CI-Coverage_average_exec_time': '122.15', 'PR-CI-Coverage_buildTime': '34.77', 'PR-CI-Coverage_testFluidLibTime': None, 'PR-CI-Coverage_testFluidLibTrainTime': None, 'PR-CI-Coverage_testCaseTime_total': '73.63', 'PR-CI-Coverage_testCaseTime_single': '53.04', 'PR-CI-Coverage_testCaseTime_multi': None, 'PR-CI-Coverage_testCaseTime_exclusive': '13.17', 'PR-CI-Coverage_fluidInferenceSize': None, 'PR-CI-Coverage_WhlSize': '823.56', 'PR-CI-Coverage_buildSize': '53.58', 'PR-CI-Coverage_testCaseCount_total': '1066.26', 'PR-CI-Coverage_testCaseCount_single': '992.64', 'PR-CI-Coverage_testCaseCount_multi': None, 'PR-CI-Coverage_testCaseCount_exclusive': '43.00', 'PR-CI-Coverage_rerunRate': '0.55', 'PR-CI-Coverage_failRate': '0.85', 'PR-CI-Inference_average_exec_time': '14.82', 'PR-CI-Inference_buildTime': '4.66', 'PR-CI-Inference_testFluidLibTime': '1.71', 'PR-CI-Inference_testFluidLibTrainTime': '0.26', 'PR-CI-Inference_testCaseTime_total': None, 'PR-CI-Inference_testCaseTime_single': None, 'PR-CI-Inference_testCaseTime_multi': None, 'PR-CI-Inference_testCaseTime_exclusive': None, 'PR-CI-Inference_fluidInferenceSize': '202.83', 'PR-CI-Inference_WhlSize': None, 'PR-CI-Inference_buildSize': None, 'PR-CI-Inference_testCaseCount_total': None, 'PR-CI-Inference_testCaseCount_single': None, 'PR-CI-Inference_testCaseCount_multi': None, 'PR-CI-Inference_testCaseCount_exclusive': None, 'PR-CI-Inference_rerunRate': '0.50', 'PR-CI-Inference_failRate': '0.61', 'PR-CI-CPU-Py2_average_exec_time': '21.37', 'PR-CI-CPU-Py2_buildTime': '2.57', 'PR-CI-CPU-Py2_testFluidLibTime': None, 'PR-CI-CPU-Py2_testFluidLibTrainTime': None, 'PR-CI-CPU-Py2_testCaseTime_total': None, 'PR-CI-CPU-Py2_testCaseTime_single': None, 'PR-CI-CPU-Py2_testCaseTime_multi': None, 'PR-CI-CPU-Py2_testCaseTime_exclusive': None, 'PR-CI-CPU-Py2_fluidInferenceSize': None, 'PR-CI-CPU-Py2_WhlSize': '89.00', 'PR-CI-CPU-Py2_buildSize': '5.80', 'PR-CI-CPU-Py2_testCaseCount_total': None, 'PR-CI-CPU-Py2_testCaseCount_single': None, 'PR-CI-CPU-Py2_testCaseCount_multi': None, 'PR-CI-CPU-Py2_testCaseCount_exclusive': None, 'PR-CI-CPU-Py2_rerunRate': '0.50', 'PR-CI-CPU-Py2_failRate': '0.82'}
    write_excel_xls(ciIndex_thisWeek, ciIndex_lastWeek)
    #send_excel(thisWeek, today)
    #ciIndex_thisWeek = {'commitCount': 375, 'PR-CI-Py35_average_exec_time': '51.50', 'PR-CI-Py35_buildTime': '7.15', 'PR-CI-Py35_testFluidLibTime': None, 'PR-CI-Py35_testFluidLibTrainTime': None, 'PR-CI-Py35_testCaseTime_total': '34.93', 'PR-CI-Py35_testCaseTime_single': '20.68', 'PR-CI-Py35_testCaseTime_multi': None, 'PR-CI-Py35_testCaseTime_exclusive': '12.57', 'PR-CI-Py35_fluidInferenceSize': None, 'PR-CI-Py35_WhlSize': '79.00', 'PR-CI-Py35_buildSize': '9.60', 'PR-CI-Py35_testCaseCount_total': '977.66', 'PR-CI-Py35_testCaseCount_single': '906.85', 'PR-CI-Py35_testCaseCount_multi': None, 'PR-CI-Py35_testCaseCount_exclusive': '41.02', 'PR-CI-Py35_rerunRate': '0.53', 'PR-CI-Py35_failRate': '0.82', 'PR-CI-Coverage_average_exec_time': '121.11', 'PR-CI-Coverage_buildTime': '32.22', 'PR-CI-Coverage_testFluidLibTime': None, 'PR-CI-Coverage_testFluidLibTrainTime': None, 'PR-CI-Coverage_testCaseTime_total': '75.63', 'PR-CI-Coverage_testCaseTime_single': '53.12', 'PR-CI-Coverage_testCaseTime_multi': None, 'PR-CI-Coverage_testCaseTime_exclusive': '15.48', 'PR-CI-Coverage_fluidInferenceSize': None, 'PR-CI-Coverage_WhlSize': '828.25', 'PR-CI-Coverage_buildSize': '54.00', 'PR-CI-Coverage_testCaseCount_total': '1066.36', 'PR-CI-Coverage_testCaseCount_single': '992.71', 'PR-CI-Coverage_testCaseCount_multi': None, 'PR-CI-Coverage_testCaseCount_exclusive': '43.00', 'PR-CI-Coverage_rerunRate': '0.51', 'PR-CI-Coverage_failRate': '0.84', 'PR-CI-Inference_average_exec_time': '13.66', 'PR-CI-Inference_buildTime': '3.69', 'PR-CI-Inference_testFluidLibTime': '1.70', 'PR-CI-Inference_testFluidLibTrainTime': '0.26', 'PR-CI-Inference_testCaseTime_total': None, 'PR-CI-Inference_testCaseTime_single': None, 'PR-CI-Inference_testCaseTime_multi': None, 'PR-CI-Inference_testCaseTime_exclusive': None, 'PR-CI-Inference_fluidInferenceSize': '202.47', 'PR-CI-Inference_WhlSize': None, 'PR-CI-Inference_buildSize': None, 'PR-CI-Inference_testCaseCount_total': None, 'PR-CI-Inference_testCaseCount_single': None, 'PR-CI-Inference_testCaseCount_multi': None, 'PR-CI-Inference_testCaseCount_exclusive': None, 'PR-CI-Inference_rerunRate': '0.47', 'PR-CI-Inference_failRate': '0.60', 'PR-CI-CPU-Py2_average_exec_time': '18.77', 'PR-CI-CPU-Py2_buildTime': '2.41', 'PR-CI-CPU-Py2_testFluidLibTime': None, 'PR-CI-CPU-Py2_testFluidLibTrainTime': None, 'PR-CI-CPU-Py2_testCaseTime_total': None, 'PR-CI-CPU-Py2_testCaseTime_single': None, 'PR-CI-CPU-Py2_testCaseTime_multi': None, 'PR-CI-CPU-Py2_testCaseTime_exclusive': None, 'PR-CI-CPU-Py2_fluidInferenceSize': None, 'PR-CI-CPU-Py2_WhlSize': None, 'PR-CI-CPU-Py2_buildSize': None, 'PR-CI-CPU-Py2_testCaseCount_total': None, 'PR-CI-CPU-Py2_testCaseCount_single': None, 'PR-CI-CPU-Py2_testCaseCount_multi': None, 'PR-CI-CPU-Py2_testCaseCount_exclusive': None, 'PR-CI-CPU-Py2_rerunRate': '0.47', 'PR-CI-CPU-Py2_failRate': '0.84'}
    #key_ci_index = keyIndicators(ciIndex_thisWeek)
    #print(key_ci_index)
    '''
    book_name_xlsx = '每周CI监控指标.xlsx'
    value_title = [["指标", "%s-%s" % (thisWeek, today), "%s-%s" % (lastWeek, thisWeek), "波动"],] 
    sheet_name_xlsx = "%s-%s" % (thisWeek, today)
    value = [["效率云平均执行时间/min", "%s" %key_ci_index['xly_average_exec_time'], "%s" %key_ci_index['xly_average_exec_time'], "杭州"]]
    write_excel_xls(book_name_xlsx, sheet_name_xlsx, value_title)
    write_excel_xls_append(book_name_xlsx, value)
    '''
main()
#write_excel_xls1()