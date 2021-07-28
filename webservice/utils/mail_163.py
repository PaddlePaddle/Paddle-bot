#!/bin/env python
# encoding: utf-8
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import socket
import traceback
import time

class Mail:
    def __init__(self):
        try:
            self.sender = 'paddlepaddle_bot@163.com'
            self.receivers = ['clzhang_cauc@163.com']
            self.subject = 'Default Title'
            self.body = MIMEText('Default Body')
        except:
            print(traceback.format_exc())

    def set_sender(self, sender='paddlepaddle_bot@163.com'):
        try:
            self.sender = sender
        except:
            print(traceback.format_exc())


    def set_receivers(self, receivers=['clzhang_cauc@163.com']):
        try:
            assert isinstance(receivers, list)
            self.receivers = list(set(receivers))
        except:
            print(traceback.format_exc())

    def set_title(self, title="Default Title"):
        try:
            self.subject = title
        except:
            print(traceback.format_exc())

    def set_message(self, message='Default Message', messageType='plain', encoding='gb2312'):
        try:
            self.body = MIMEText(message, messageType, encoding)
        except:
            print(traceback.format_exc())

    def send(self):
        try:
            mail = MIMEMultipart('mail')
            mail['From'] = self.sender
            strTo = ",".join(self.receivers)
            mail['To'] = strTo
            mail['Subject'] = self.subject
            mail.attach(self.body)
            smtpObj = smtplib.SMTP_SSL('smtp.163.com', 465)
            smtpObj.login('paddlepaddle_bot@163.com', 'HEMKWWPZKFYJXBRZ')
            smtpObj.sendmail(self.sender, self.receivers, mail.as_string())
        except:
            print(traceback.format_exc())