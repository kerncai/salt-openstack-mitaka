#!/usr/bin/env python
# coding=utf-8
#	 > File Name: saltapi_python.py
#	 > Author: kerncai
#	 > Email: kernkerncai@gmail.com
#	 > Created Time: Thu 16 Feb 2017 07:02:00 PM CST
#########################################################
import salt.client
import salt.runner
import time

local = salt.client.LocalClient()

class login:
   
    def saltcmd(self,tgt,cmd):
        jid = local.cmd_async(tgt,'state.sls',expr_form='list',kwarg={'mods':'%s' %cmd})
        return jid

    def status_jid(self,tgt,cmd):
        jid = self.saltcmd(tgt,cmd)
        t = 0
        flag = 0
        if ',' in tgt:
            hosts = tgt.split(',')
            num = len(hosts)
        else:
            num = 1
        status_list = []
        while not local.get_cache_returns(jid) or len(local.get_cache_returns(jid)) != num:
            time.sleep(6)
            if t == 200:
                break
            else:
                t+=1
        message = local.get_cache_returns(jid)
    
        for i in message:
            for j in message[i]:
                for k in message[i]["ret"]:
                    for h in  message[i]["ret"][k]:
                        result = message[i]["ret"][k]["result"]
                        if str(result) == 'True':
                            flag = 1
                        else:
                            flag = 0
                
            status_list.append({'hostname':i,'status':flag})
        return status_list

    def statusjid(self,tgt,cmd):
        hostname_list = []
        t = 0 
        return_status = self.status_jid(tgt,cmd)
        if len(return_status) > 0:
            for i in return_status:
                status = i['status']
                while status == 0:
                    again_status = self.status_jid(i['hostname'],cmd)
                    for j in again_status:
                        i['status'] = j['status']
                    if t == 1:
                        break
                    else:
                        t+=1
                hostname_list.append(i['hostname'])
                if i['hostname'] not in tgt:
                    next_status = self.status_jid(i['hostname'],cmd)
                    return_status.append(next_status)
                else:
                    pass
        else:
            return_status = self.status_jid(tgt,cmd)
        return return_status





    def testping(self,tgt):
        status = []
        ret = local.cmd_iter(tgt,'test.ping',expr_form='list',timeout=10)
        for i in ret:
            for key in i:
                status.append(key)
        return status
    
    def refresh_pillar(self,tgt):
        local.cmd_async(tgt,'saltutil.refresh_pillar',expr_form='list',timeout=30)

    def sync_grains(self,tgt):
        local.cmd_async(tgt,'sync_grains',expr_form='list',timeout=30)

    def check_osd(self,tgt,cmd):
        osd_status = []
        try:
            for status in local.cmd_iter(tgt,'state.sls',kwarg={'mods':'%s' %cmd},timeout=50):
                for i in status:
                    for j in status[i]:
                        for k in  status[i]['ret']:
                            for h in  status[i]['ret'][k]:
                                for o in status[i]['ret'][k]['changes']:
                                    osd_status.append(status[i]['ret'][k]['changes']['stdout'])
        except Exception as e:
            print e
        if len(list(set(osd_status))) > 0:
            return_status = list(set(osd_status))[0]
        else:
            return_status = "kerncai_osd_error"
        return return_status

    def check_osd_status(self,tgt,cmd):
        status = self.check_osd(tgt,cmd)
        if status == "kerncai_osd_success":
            return 1
        elif status == "kerncai_osd_error":
            return 0

if __name__ == '__main__':
    #测试使用，用作类的时候，以下不会使用
    tgt = "ceph-kerncai-001"
    fun = "state.sls"
    cmd = "ceph.ceph-deploy.ceph-deploy-check"
    run = login()
    run.check_osd_status(tgt,cmd)
    del run
