#!/usr/bin/env python
# -*- coding: utf-8 -*-
import SocketServer
import json
import struct
import fcntl
import socket
import threading


TCPServerPort = 60001
UDPPort = 60002

host = ''
addr = (host,UDPPort)


def getip(ethname):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24])


def setMessage(mes):
    sockLocal.send(mes)
def reConnect(msg):
    global sockLocal
    sockLocal = doConnect('127.0.0.1', TCPServerPort)
    setMessage(msg)

class Servers(SocketServer.BaseRequestHandler):
    def handle(self):
        data =self.request[0]
        print(data.decode('utf-8'))
        #print(self.client_address,self.request[1])
        #self.request[1].sendto('bbb'.encode('utf-8'), self.client_address)
        try:
            setMessage(data.decode('utf-8'))
        except socket.error:
            print '\r\nsocket error occur '
            reConnect(data.decode('utf-8'))
        except:
            print '\r\nother error occur '
def doConnect(host,port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try :
        sock.connect((host,port))
    except :
        pass
    return sock
if __name__=='__main__':

    try:
		print getip('eth0')
		host = getip('eth0')
    except:
		print 'Not net connect!'
    print 'UDP server is running....'
    print 1
    sockLocal = doConnect('127.0.0.1', TCPServerPort)
    print 2
    server = SocketServer.ThreadingUDPServer(addr, Servers)
    print 3
    server_thread = threading.Thread(target=server.serve_forever)
    #server_thread.daemon = True
    server_thread.start()
    print "Server loop running in thread:", server_thread.name
    #server.serve_forever()
    print 4





