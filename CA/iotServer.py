#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aliyunsdkcore import client
from aliyunsdkiot.request.v20170420 import RegistDeviceRequest
from aliyunsdkiot.request.v20170420 import PubRequest


accessKeyId = 'wCnHWwg79kH'
accessKeySecret = '75HdE2s6yMF5wv6eVPVnotPSzni4tOoN'
clt = client.AcsClient(accessKeyId, accessKeySecret, 'smartcontroller001')

request = PubRequest.PubRequest()
request.set_accept_format('json')  #设置返回数据格式，默认为XML
request.set_ProductKey('productKey')
request.set_TopicFullName('/productKey/deviceName/get')  #消息发送到的Topic全名
request.set_MessageContent('aGVsbG8gd29ybGQ=')  #hello world Base64 String
request.set_Qos(0)
result = clt.do_action(request)
print 'result : ' + result

if __name__=='__main__':
	print "UDP Server is running..."