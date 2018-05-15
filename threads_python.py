#!/usr/bin/env python
# coding=utf-8
#	 > File Name: threads_python.py
#	 > Author: kerncai
#	 > Email: kernkerncai@gmail.com
#	 > Created Time: Sun 19 Feb 2017 06:55:59 PM CST
#########################################################
import threading

class run:

    def threads_define(self,func1,func2):
        threads = []
        t1 = threading.Thread(func1)
        threads.append(t1)
        t2 = threading.Thread(func2)
        threads.append(t2)
        return threads

    def threads_action(self,func1,func2):
        threads = self.threads_define(func1,func2)
        for t in threads:
            t.setDaemon(True)
            t.start()
        t.join()
