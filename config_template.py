#!/usr/bin/env python
# coding=utf-8
#	 > File Name: config_template.py
#	 > Author: kerncai
#	 > Email: kernkerncai@gmail.com
#	 > Created Time: Fri 17 Feb 2017 07:35:02 PM CST
#########################################################

import os 

class run:

    def config_template(self,file,_from,_to):
        sed_cmd = """sed -i "s/%s/%s/g" %s """ %(_from,_to,file)
        os.system(sed_cmd)



