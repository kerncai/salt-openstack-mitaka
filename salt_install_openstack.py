#!/usr/bin/env python
# coding=utf-8
#	 > File Name: kerncai_config.py
#	 > Author: kerncai
#	 > Email: kernkerncai@gmail.com
#	 > Created Time: Wed 15 Feb 2017 10:13:19 AM CST
#########################################################

import os
import sys
import time
import config_template
import obj_logging
import saltapi_python
import ConfigParser
import threads_python
import commands

class openstack_config:

    def __init__(self):
        self.config_path = "kerncai_openstack_automation.cfg"
        self.config_template_file = "/usr/local/scripts/openstack/.config.template"
        self.ceph_template_file = "/usr/local/scripts/openstack/.config.ceph"
        self.pillar_openstack_ha = "/srv/salt/pillar/openstack_ha/config.sls"
        self.pillar_ceph = "/srv/salt/pillar/ceph/ceph.sls"
        self.hosts_path = "/srv/salt/openstack_ha/system/host/hosts"
        self.install_log = "/var/log/kerncai/"
        self.logger = obj_logging.Logger("%s/salt_install_openstack_ceph.log" %self.install_log)
        self.salt_action = saltapi_python.login()
        self.config_template = config_template.run()
        self.threads = threads_python.run()

    def mkdir_log(self):
        if not os.path.exists(self.install_log):
            os.makedirs(self.install_log)
        print "You can use the log  %ssalt_install_openstack_ceph.log to check the details of installation" %(self.install_log)
        os.system("rm -f %s" %self.pillar_openstack_ha)
        os.system("cp -rp %s %s" %(self.config_template_file,self.pillar_openstack_ha))
        os.system("rm -f %s" %self.pillar_ceph)
        os.system("cp -rp %s %s" %(self.ceph_template_file,self.pillar_ceph))


    def read_config(self):
        config = ConfigParser.SafeConfigParser()
        config.read(self.config_path)
        return config

    def get_default(self):
        #读取default内的配置
        default_config = []
        read_config = self.read_config()
        default = read_config.options('default')
        for key in default:
            value = read_config.get('default',key)
            default_config.append({key:value})
        return default_config

    def get_item(self,item):
        #读取非default内的配置
        item_config = []
        read_config = self.read_config()
        if item != "ceph":
            item_list = read_config.options(item)
            for key in item_list:
                value = read_config.get(item,key)
                node = value.split(',')
                idrac = node[0]
                hostname = node[1]
                manageip = node[2]
                item_config.append({"idrac":idrac,"hostname":hostname,"manageip":manageip})
        else:
            ceph = read_config.options('ceph')
            for key in ceph:
                value = read_config.get('ceph',key)
                item_config.append({key:value})
            
        return item_config
    
    def get_openstack_controller(self):
        return self.get_item("openstack_controller")

    def get_openstack_compute(self):
        return self.get_item("openstack_compute")

    def get_openstack_network(self):
        return self.get_item("openstack_network")

    def get_ceph(self):
        return self.get_item("ceph")

    def get_ceph_mon_node(self):
        return self.get_item("ceph_mon_node")

    def get_ceph_osd_node(self):
        return self.get_item("ceph_osd_node")

    def report_config(self):
        os.system('cat %s|grep -vE "^#|^$"' %self.config_path)

    def get_input(self):
        _raw_input = raw_input("Please confirm the current configuration is yours? \n yes(y/Y)/no(N/n)/? \n" )
        if _raw_input == 'yes' or _raw_input == 'Y' or _raw_input == 'y':
            pass
        elif _raw_input == 'no' or _raw_input == 'N' or _raw_input == 'n':
            print 'Select no,exit!'
            sys.exit(1)

    
    def get_init_nodes(self,nodes):
        init_nodes = nodes
        init_node_list = []
        for i in init_nodes:
            init_node_list.append(i['hostname'])
        init_node = ",".join(init_node_list)
        return init_node

    def install_node_template(self,salt_nodes,salt_mods):
        if len(salt_nodes) > 0:
            nodes = []
            for salt_node in salt_nodes.split(','):
                self.logger.info('install  %s  %s starting' %(salt_node,salt_mods))
            return_status = self.salt_action.statusjid(salt_nodes,salt_mods)
            for i in return_status:
                if i['status'] == 1:
                    nodes.append(i['hostname'])
                    self.logger.info('install  %s  %s  Success.' %(i['hostname'],salt_mods))
                else:
                    self.logger.error('install  %s  %s Failed.' %(i['hostname'],salt_mods))
            for i in salt_nodes.split(','):
                if i not in nodes:
                    self.logger.error('install  %s  %s Failed.' %(i,salt_mods))
        else:
            self.logger.error('install  %s is null,sys.exit' %salt_nodes)
            sys.exit(1)


        return ','.join(nodes)

    def write_pillar_config(self):
        #生成default内配置信息
        default = self.get_default()
        vip = []
        for i in default:
            for j in i:
                if j == "admin_token":
                    admin_token = i[j]
                    fromold = "ADMIN_TOKEN: node"
                    tonew = "ADMIN_TOKEN: %s" %admin_token
                    self.config_template.config_template(self.pillar_openstack_ha,fromold,tonew)
                elif j == "local_manage_adapter":
                    _from = "local_ip: node"
                    _to = "local_ip: {{ grains['ip_interfaces']['%s'][0] }}" %i[j]
                    self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
                    _from = "wsrep_node_address: node"
                    _to = "wsrep_node_address: {{ grains['ip_interfaces']['%s'][0] }}" %i[j]
                    self.config_template.config_template(self.pillar_openstack_ha,_from,_to)

                elif j == "local_privately_adapter":
                    _from = "local_privately_ip: node"
                    _to = "local_privately_ip: {{ grains['ip_interfaces']['%s'][0] }}" %i[j]
                    self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
                elif j == "local_ceph_data_adapter":
                    _from = "mon_ip: node"
                    _to = "mon_ip: {{ grains['ip_interfaces']['%s'][0] }}" %i[j]
                    self.config_template.config_template(self.pillar_ceph,_from,_to)
                elif j == "openstack_ha_cluster_vip":
                    vip.append(i[j])
        # 生成VIP配置信息
        if not vip[0].strip():
            self.logger.error("read  openstack_ha_cluster_vip is null,please check it agian.")
            sys.exit(1)
        else:
            _to = "haproxy_vip: %s" %vip[0]
            _from = "haproxy_vip: node"
            self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
            _to = "pacemake_init_vip: %s" %vip[0]
            _from = "pacemake_init_vip: node"
            self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        #生成controller相关信息
        self.logger.info("reset initialization  openstack configuration environment")
        controller = sorted(self.get_openstack_controller())
        controller_hostname = []
        controller_ip = []
        for i in controller:
            host_name = i['hostname']
            manageip = i['manageip']
            controller_hostname.append(host_name)
            controller_ip.append(manageip)
        print controller_hostname,controller_ip
        controller_master_hostname = controller_hostname[0]
        _from = "wsrep_node_init_master: node"
        _to = "wsrep_node_init_master: %s" %controller_master_hostname
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "cluster_node_init_master: node"
        _to = "cluster_node_init_master: %s" %controller_master_hostname
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "pacemake_init_master: node"
        _to = "pacemake_init_master: %s" %controller_master_hostname
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "rabbitmq_cluster_node: node"
        _to = "rabbitmq_cluster_node: %s:5672,%s:5672,%s:5672" %(controller_hostname[0],controller_hostname[1],controller_hostname[2])
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "pacemake_init_node: node"
        _to = "pacemake_init_node: %s,%s,%s" %(controller_hostname[0],controller_hostname[1],controller_hostname[2])
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "memcache_cluster_node: node"
        _to = "memcache_cluster_node: %s:11211,%s:11211,%s:11211" %(controller_hostname[0],controller_hostname[1],controller_hostname[2])
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "haproxy_node1: node"
        _to = "haproxy_node1: %s" %controller_ip[0]
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "haproxy_node2: node"
        _to = "haproxy_node2: %s" %controller_ip[1]
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "haproxy_node3: node"
        _to = "haproxy_node3: %s" %controller_ip[2]
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        _from = "wsrep_cluster_address: node"
        _to = "wsrep_cluster_address: gcomm:\/\/%s,%s,%s" %(controller_ip[0],controller_ip[1],controller_ip[2])
        self.config_template.config_template(self.pillar_openstack_ha,_from,_to)
        self.logger.info("reset init openstack config done")
        #生成ceph配置信息
        network = self.get_openstack_network()
        for i in network:
            controller_hostname.append(i["hostname"])
        compute = self.get_openstack_compute()
        for i in compute:
            controller_hostname.append(i["hostname"])
        openstack = sorted(list(set(controller_hostname)))
        ceph = self.get_ceph()
        ceph_mon = sorted(self.get_ceph_mon_node())
        ceph_mon_host = []
        ceph_mon_ip = []
        ceph_deploy = []
        for i in ceph_mon:
            ceph_deploy.append(i['hostname'])
            ceph_mon_host.append(i['hostname'])
            ceph_mon_ip.append(i['manageip'])
        if not ceph_deploy[0].strip():
            self.logger.error("read ceph mode node is null,please check it agian")
            sys.exit(1)
        else:
            for i in ceph:
                for j in i:
                    if j == "public_network":
                        _from = "public_network: node"
                        _to = "public_network: %s" %i[j].replace('/','\/')
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "ceph_deploy":
                        _from = "ceph_deploy: node"
                        if not i[j].strip():
                            _to = "ceph_deploy: %s" %ceph_deploy[0]
                        else:
                            _to = "ceph_deploy: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_journal_size":
                        _from = "osd_journal_size: node"
                        _to = "osd_journal_size: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_journal_num":
                        _from = "osd_journal_num: node"
                        _to = "osd_journal_num: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_hdd_min_size":
                        _from = "osd_hdd_min_size: node"
                        _to = "osd_hdd_min_size: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_hdd_max_size":
                        _from = "osd_hdd_max_size: node"
                        _to = "osd_hdd_max_size: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_ssd_min_size":
                        _from = "osd_ssd_min_size: node"
                        _to = "osd_ssd_min_size: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "osd_ssd_max_size":
                        _from = "osd_ssd_max_size: node"
                        _to = "osd_ssd_max_size: %s" %i[j]
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                    elif j == "openstack_node":
                        _from = "openstack_node: node"
                        openstack_node = ",".join(openstack)
                        _to = "openstack_node: %s" %openstack_node
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                        _from = "mon_initial_members: node"
                        mon_initial_members = ",".join(ceph_mon_host)
                        _to = "mon_initial_members: %s" %mon_initial_members
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                        _from = "mon_host_mem: node"
                        mon_host = ",".join(ceph_mon_ip)
                        _to = "mon_host_mem: %s" %mon_host
                        self.config_template.config_template(self.pillar_ceph,_from,_to)
                        self.logger.info("reset init %s config done" %self.pillar_ceph)

    def get_singel_host(self):
        #解析配置文件，并将涉及到的所有hostname去重
        cluster_nodes = []
        controller = self.get_openstack_controller()
        for i in controller:
            cluster_nodes.append({i['hostname']:i['manageip']})
        compute = self.get_openstack_compute()
        for i in compute:
            if {i['hostname']:i['manageip']} not in cluster_nodes:
                cluster_nodes.append({i['hostname']:i['manageip']})
            else:
                pass
        network = self.get_openstack_network()
        for i in network:
            if {i['hostname']:i['manageip']} not in cluster_nodes:
                cluster_nodes.append({i['hostname']:i['manageip']})
            else:
                pass
        ceph_mon_node = self.get_ceph_mon_node()
        for i in ceph_mon_node:
            if {i['hostname']:i['manageip']} not in cluster_nodes:
                cluster_nodes.append({i['hostname']:i['manageip']})
            else:
                pass
        ceph_osd_node = self.get_ceph_osd_node()
        for i in ceph_osd_node:
            if {i['hostname']:i['manageip']} not in cluster_nodes:
                cluster_nodes.append({i['hostname']:i['manageip']})
            else:
                pass
        return cluster_nodes

    def check_minion_status(self):
        #使用配置文件内得到的hostname，去进行test.ping检测，返回一个list，为空表示全部可达，非空为异常
        config_host = self.get_singel_host()
        hosts = []
        for i in config_host:
            for key in i:
                hosts.append(key)
        host_list = ",".join(hosts) 
        host_status = self.salt_action.testping(host_list)
        unreachable_hosts = []
        for i in hosts:
            if i not in host_status:
                unreachable_hosts.append(i)
                self.logger.error("check  "+ i + "  Minion did not return. [Not connected]")
            else:
                pass
        return unreachable_hosts

    def set_hosts(self):
        #读取配置后，生成hosts配置文件，然后使用salt推送 
        host_dict = self.get_singel_host()
        os.system("rm -rf %s" %self.hosts_path)
        nic = open(self.hosts_path,"a")
        self.logger.info("read  " + "starting to read config")
        try:
            nic.write("127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4" + '\n' + "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6" + '\n')
            for host in host_dict:
                for key in host:
                    self.logger.info("reset  " + self.config_path + "  " + host[key]  + "  " + key)
                    nic.write(host[key]  + "    " + key + '\n')
        except Exception,e:
            self.logger.error("reset  " + Exception,":",e)
        nic.close()
        salt_mods = "openstack_ha.system.host.hosts"
        host_list = []
        for i in host_dict:
            for j in i:
                host_list.append(j)
        host_str = ','.join(host_list)
        self.logger.info('reset  %s sync_grains and refresh_pillar.'% host_str) 
        self.salt_action.refresh_pillar(host_str)
        time.sleep(45)
        self.salt_action.sync_grains(host_str)
        return_status = self.salt_action.statusjid(host_str,salt_mods)
        for i in return_status:
            if i['status'] == 1:
                self.logger.info("install  %s  %s success." %(i['hostname'],salt_mods))
                self.salt_action.refresh_pillar(host_str)
                self.logger.info("install  %s update minion pillar data." %i['hostname'])
            else:
                self.logger.info("install  %s  %s Failed." %(i['hostname'],salt_mods))
                sys.exit(1)
        
    def install_openstack_controller(self):
        controller = self.get_init_nodes(self.get_openstack_controller())
        mods = "openstack_ha.openstack_client"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.memcache.memcache"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.mariadb.mariadb"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.rabbitmq.rabbitmq"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.haproxy.haproxy"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.pacemaker.pacemaker"
        self.install_node_template(controller,mods)
        self.salt_action.sync_grains(controller)
        mods = "openstack_ha.keystone.keystone"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.glance.glance"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.nova.nova"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.neutron.controller.neutron_controller"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.cinder.cinder"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.dashboard.dashboard"
        self.install_node_template(controller,mods)
        compute = self.get_init_nodes(self.get_openstack_compute())
        mods = "openstack_ha.nova.nova_compute"
        self.install_node_template(compute,mods)
        mods = "openstack_ha.neutron.compute.neutron_compute"
        self.install_node_template(compute,mods)
        network = self.get_init_nodes(self.get_openstack_network())
        mods = "openstack_ha.neutron.network.neutron_network"
        self.install_node_template(network,mods)

    def install_ceph(self):
        ceph_mon_node = self.get_init_nodes(self.get_ceph_mon_node())
        self.salt_action.refresh_pillar(ceph_mon_node)
        mods = "system_ceph"
        self.install_node_template(ceph_mon_node,mods)
        mods = "ceph.ceph-deploy.ceph-deploy-pkg"
        self.install_node_template(ceph_mon_node,mods)
        mods = "ceph.ceph-deploy.ceph-deploy-mon"
        self.install_node_template(ceph_mon_node,mods)
        ceph_osd_node = self.get_init_nodes(self.get_ceph_osd_node())
        ceph_osd_node_list = sorted(ceph_osd_node.split(','))
        t = 0
        mods = "ceph.ceph-deploy.ceph-deploy-osd"
        for i in ceph_osd_node_list:
            self.logger.info('install  %s  %s starting' %(i,mods))
            status = self.salt_action.statusjid(i,mods)
            if len(status) > 0:
                if status[0]['status'] == 1:
                    self.logger.info('install  %s  %s  Success.' %(status[0]['hostname'],mods))
                    salt_cmd = "salt -L '%s' state.sls ceph.ceph-deploy.ceph-deploy-check" %i
                    return_status = commands.getoutput(salt_cmd)
                    s_flag = "kerncai_osd_success"
                    e_flag = "kerncai_osd_error"
                    while e_flag in return_status:
                        if t > 3:
                            self.logger.error('checkout  %s osd nums Error.Repeated 2,exit!' %i)
                            sys.exit(1)
                        else:
                            self.logger.info('checkout %s osd nums Error,zap disk and try osd again,now %s' %(i,t))
                            mods = "ceph.ceph-deploy.ceph-deploy-clean"
                            self.salt_action.statusjid(i,mods)
                            mods = "ceph.ceph-deploy.ceph-deploy-osd"
                            self.salt_action.statusjid(i,mods)
                            return_status = commands.getoutput(salt_cmd)
                            t+=1
                        
                    if s_flag in return_status:
                        self.logger.info('checkout  %s  osd nums  Success.' %i)
                else:
                    self.logger.error('install  %s  %s  Failed..' %(status[0]['hostname'],mods))
                    sys.exit(1)
            else:
                self.logger.error('install  %s  %s  Failed..' %(status[0]['hostname'],mods))
                sys.exit(1)

    def install_openstack_ceph(self):
        controller = self.get_init_nodes(self.get_openstack_controller())
        mods = "openstack_ha.system.host.hosts"
        self.install_node_template(controller,mods)
        ceph_deploy_node = self.get_ceph_mon_node()
        ceph_deploy_node_list = []
        for deploy in ceph_deploy_node:
            ceph_deploy_node_list.append(deploy['hostname'])
        ceph_deploy_master = sorted(ceph_deploy_node_list)[0]
        mods = "ceph.ceph-deploy.ceph-deploy-pool"
        self.install_node_template(ceph_deploy_master,mods)
        compute = self.get_init_nodes(self.get_openstack_compute())
        mods = "openstack_ha.openstack_ceph.ceph_key_controller"
        self.install_node_template(controller,mods)
        mods = "openstack_ha.openstack_ceph.ceph_key_compute"
        self.install_node_template(compute,mods)
        controller_master_list = []
        controller_dic = self.get_openstack_controller()
        for i in controller_dic:
            controller_master_list.append(i['hostname'])
        controller_master = controller_master_list[0]
        mods = "openstack_ha.glance.glance-add-image"
        self.install_node_template(controller_master,mods)
        self.logger.info('install  install successfully on each openstack node.')
        self.logger.info('checkout  try to created an instance to test function module')
        mods = "salt -L '%s' state.sls openstack_ha.create_instance.create_instance" %controller_master
        os.system(mods)


    def _install_openstack_ceph(self):
        self.threads.threads_action(self.install_openstack_controller(),self.install_ceph())


if __name__ == "__main__":
    run = openstack_config()
    run.mkdir_log()
    run.write_pillar_config()
    test_ping_status = run.check_minion_status()
    if len(test_ping_status) > 0:
        print "%s did not return. [Not connected]" %test_ping_status
        sys.exit(1)
    else:
        run.report_config()
        run.get_input()
        run.set_hosts()
        run.install_ceph()
        run._install_openstack_ceph()
        run.install_openstack_ceph()
    del run 
