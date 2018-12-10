#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aliyunsdkcore import client
from aliyunsdkiot.request.v20170420 import RegistDeviceRequest
from aliyunsdkiot.request.v20170420 import PubRequest


accessKeyId = 'LTAI3F1lpJkbiJtx'
accessKeySecret = 'MqFwXFCeDHPfgdMI6YOBIMqV9vEUrf'
clt = client.AcsClient(accessKeyId, accessKeySecret, 'cn-shanghai')



if __name__=='__main__':

    request = PubRequest.PubRequest()
    request.set_accept_format('json')  # 设置返回数据格式，默认为XML
    request.set_ProductKey('wCnHWwg79kH')
    request.set_TopicFullName('/wCnHWwg79kH/smartcontroller001/get')  # 消息发送到的Topic全名
    request.set_MessageContent('aGVsbG8gd29ybGQ=')  # hello world Base64 String
    request.set_Qos(0)
    result = clt.do_action_with_exception(request)
    print 'result : ' + result