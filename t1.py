#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import time

def sayhi(num):
    print('running on nuber:%s' %num)
    time.sleep(3)

if __name__=='__main__':
    t_list = []
    for i in range(20):
        t = threading.Thread(target=sayhi,args=[i,])
        t.start()
        t_list.append(t)
    for i in t_list:
        i.join()
    print('----done——')