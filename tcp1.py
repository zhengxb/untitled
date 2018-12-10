#!/usr/bin/env python
# -*- coding: utf-8 -*-
import SocketServer
import threading

from twisted.internet import threads


def tcpserverstart(self):
    host, port = "127.0.0.1", 8008
    server = SocketServer.ThreadingTCPServer((host, port), MyTCPHandler)
    server.serve_forever()
class MyTCPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        while True: #可以重复接收
            #等待客户端的链接，接收数据
            self.data = self.request.recv(1024).strip()
            #打印客户端的地址
            print("{}wrote".format(self.client_address[0]))
            #打印客户端发来的信息
            print(self.data)
            #将客户端发来的信息变成大写病返回
            self.request.sendall(self.data.upper())


if __name__ == "__main__":
    tcps = threading.Thread(target = tcpserverstart, args = None)
    threads.append(tcps)
    for i in range(len(threads)):  # 启动线程
        threads[i].start()
    threads[0].join()
    print 1