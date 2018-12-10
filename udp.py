# -*- coding: utf-8 -*-
from socket import *
import struct
import fcntl

HOST = '<broadcast>'
PORT = 21567
BUFSIZE = 1024

ADDR = (HOST, PORT)

def getip(ethname):
	s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24])


udpCliSock = socket(AF_INET, SOCK_DGRAM)
udpCliSock.bind(('', 0))
udpCliSock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
while True:
    data = raw_input('>')
    if not data:
        break
    print "sending -> %s"%data
    print getip('eth0')
    udpCliSock.sendto(getip('eth0'),ADDR)
##    data,ADDR = udpCliSock.recvfrom(BUFSIZE)
##    if not data:
##        break
##    print data

udpCliSock.close()