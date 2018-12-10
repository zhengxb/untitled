#!/usr/bin/env python
# -*- coding: utf-8 -*-
import SocketServer
import json
import struct
import fcntl
import socket
port = 5007
host = ''
addr = (host,port)
if __name__=='__main__':
    try:
		print getip('eth0')
		host = getip('eth0')
    except:
		print 'Not net connect!'
def getip(ethname):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24])

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        print "Send: {}".format(message)
        sock.sendall(message)
        response = sock.recv(1024)
        #jresp = json.loads(response)
        print "Recv: ", response
    finally:
        sock.close()

class Servers(SocketServer.BaseRequestHandler):
    def handle(self):
        data =self.request[0]
        print(data.decode('utf-8'))
        print(self.client_address,self.request[1])
        self.request[1].sendto('bbb'.encode('utf-8'), self.client_address)
        client('192.168.1.106', 12345, data.decode('utf-8'))
print 'server is running....'
server = SocketServer.ThreadingUDPServer(addr,Servers)
server.serve_forever()




