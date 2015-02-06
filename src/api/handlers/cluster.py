#-*- coding: utf-8 -*-

from common.configFileOpers import ConfigFileOpers
from common.invokeCommand import InvokeCommand
from base import APIHandler
from common.tornado_basic_auth import require_basic_auth
from common.helper import issue_mycnf_changed, get_zk_address
from common.cluster_mysql_service_opers import Cluster_Mysql_Service_Opers
from tornado.options import options
from tornado.web import asynchronous
from tornado.gen import engine
from common.utils.exceptions import HTTPAPIError
from common.zkOpers import ZkOpers

import logging
import uuid
import kazoo

'''
Created on 2013-7-21

@author: asus
'''

# create mcluster
# eg. curl --user root:root -d "clusterName=letv_mcluster_test_1&dataNodeIp=192.168.0.10&dataNodeName=letv_mcluster_test_1_node_1" "http://localhost:8888/cluster"
@require_basic_auth
class CreateMCluster(APIHandler):
    
    confOpers = ConfigFileOpers()
    
    def post(self):
        #check if exist cluster
        zk_address = get_zk_address()
        zkoper_obj = ZkOpers(zk_address, 2181)
        existCluster = zkoper_obj.existCluster()
        requestParam = {}
        args = self.request.arguments
        if existCluster:
            raise HTTPAPIError(status_code=417, error_detail="server has belong to a cluster,should be not create new cluster!",\
                                notification = "direct", \
                                log_message= "server has belong to a cluster,should be not create new cluster!",\
                                response =  "the server has belonged to a cluster,should be not create new cluster!")
        
        requestParam = {}
        args = self.request.arguments
        logging.info("args :" + str(args))
        for key in args:
            value = args[key][0]
            requestParam.setdefault(key,value)
        cluster_name = requestParam['clusterName']
        if len(cluster_name) >= 33:
            raise HTTPAPIError(status_code=403, error_detail="Cluster name is too long, please use name whoes length is less than 33 characters",\
                                notification = "direct", \
                                log_message= "Cluster name is too long, please use name whoes length is less than 33 characters",\
                                response =  "Cluster name is too long, please use name whoes length is less than 33 characters!")
        clusterUUID = str(uuid.uuid1())
        requestParam.setdefault("clusterUUID",clusterUUID)
        
        if requestParam != {}:
            self.confOpers.setValue(options.cluster_property, requestParam)
            self.confOpers.setValue(options.data_node_property, requestParam)
            
        clusterProps = self.confOpers.getValue(options.cluster_property)
        dataNodeProprs = self.confOpers.getValue(options.data_node_property)
        zkoper_obj.writeClusterInfo(clusterUUID, clusterProps)
        zkoper_obj.writeDataNodeInfo(clusterUUID, dataNodeProprs)
        
        dict = {}
#        dict.setdefault("code", '000000')
        dict.setdefault("message", "creating cluster successful!")
        self.finish(dict)
        zkoper_obj.close()       
        
# init mcluster
# eg. curl --user root:root "http://localhost:8888/cluster/init?forceInit=false"
@require_basic_auth
class InitMCluster(APIHandler):
    
    confOpers = ConfigFileOpers()
    
    invokeCommand = InvokeCommand()
    
    def get(self):
        args = self.request.arguments
        forceInit = args['forceInit'][0]
            
        isLock = False
        lock = None
        
        try:
            zk_address = get_zk_address()
            zkoper_obj = ZkOpers(zk_address, 2181)
            existCluster = zkoper_obj.existCluster()

            isLock,lock = zkoper_obj.lock_init_node_action()
        except kazoo.exceptions.LockTimeout:
            raise HTTPAPIError(status_code=578, error_detail="a server is initing, need to wait for the completion of init oper.",\
                                notification = "direct", \
                                log_message= "a server is initing, need to wait for the completion of init oper.",\
                                response =  "the mysql cluster is initing,please wait for the completion of other machine join this cluster.")
        
        try:
            dataNodeProKeyValue = self.confOpers.getValue(options.data_node_property, ['dataNodeIp','dataNodeName'])
            data_node_ip = dataNodeProKeyValue['dataNodeIp']
            data_node_name = dataNodeProKeyValue['dataNodeName']
            
            clusterProKeyValue = self.confOpers.getValue(options.cluster_property, ['clusterUUID','clusterName'])
            clusterUUID = clusterProKeyValue['clusterUUID']
            
            #check if cluster has odd data node
            if not forceInit:
                dataNodeNumber = zkoper_obj.getDataNodeNumber(clusterUUID)
                if dataNodeNumber/2 == 0:
                    raise HTTPAPIError(status_code=417, error_detail="the server number of cluster should be odd number",\
                                    notification = "direct", \
                                    log_message= "the server number of cluster should be odd number",\
                                    response =  "the number should be not odd number,please add 1 or 3 data node into cluster!")
            
            clusterName = clusterProKeyValue['clusterName']
            clusterAddress = 'gcomm://' + data_node_ip
            
            requestParam = {'wsrep_cluster_name':clusterName, 'wsrep_node_address':data_node_ip, 'wsrep_cluster_address':clusterAddress, 'wsrep_node_name':data_node_name}
            self.confOpers.setValue(options.mysql_cnf_file_name, requestParam)
            
            sst_user_password = self.invokeCommand.runBootstrapScript()
            #self.zkOper = ZkOpers('127.0.0.1',2181)
            #logging.info("init zk")
            zkoper_obj.write_started_node(data_node_ip)
                
            
#            mysql_cnf_text_test = self.confOpers.retrieveFullText(options.mysql_cnf_file_name)
            
            mysql_cnf_text = self.confOpers.retrieveFullText(options.mysql_cnf_file_name)
            zkoper_obj.writeMysqlCnf(clusterUUID, mysql_cnf_text, issue_mycnf_changed)
        except Exception, e:
            logging.error(e)
            raise HTTPAPIError(status_code=500, error_detail="server_error",
                               notification = "direct",
                               log_message= "server_error",
                               response =  "server_error")
            
        finally:
            zkoper_obj.unLock_init_node_action(lock)
        
        dict = {}
#        dict.setdefault("code", '000000')
        dict.setdefault("message", "init cluster successful!")
        dict.setdefault("sst_user_password", sst_user_password)
        self.finish(dict)
        zkoper_obj.close()
        
# sync mcluster
# eg. curl "http://localhost:8888/cluster/sync"
class SyncMCluster(APIHandler):
    
    confOpers = ConfigFileOpers()
    
    def get(self):
        zk_address = get_zk_address()
        zkoper_obj = ZkOpers(zk_address, 2181)
        existCluster = zkoper_obj.existCluster()

        clusterUUID = zkoper_obj.getClusterUUID()
        data, stat = zkoper_obj.retrieveClusterProp(clusterUUID)
        self.confOpers.setValue(options.cluster_property, eval(data))
        
        dict = {}
 #       dict.setdefault("code", '000000')
        dict.setdefault("message", "sync mcluster info to local successful!")
        self.finish(dict)
        zkoper_obj.close()
        
        
# start mysqld service on every data node for entity cluster
# eg. curl --user root:root -d "cluster_flag=new" "http://localhost:8888/cluster/start"
@require_basic_auth
class ClusterStart(APIHandler):
    
    mysql_service_opers = Cluster_Mysql_Service_Opers()

    @asynchronous
    def post(self):
        args = self.request.arguments
        logging.info("args :" + str(args))
        for key in args:
            value = args[key][0]
        if value != 'new' and value != 'old':
            raise HTTPAPIError(status_code=-1, error_detail="arguments are wrong",
                               notification = "direct",
                               log_message= "arguments are wrong",
                               response =  "arguments are wrong, retry again.")
        logging.info("Arguments in Http requests is " + value)
        try:
            self.mysql_service_opers.start(value)
        except kazoo.exceptions.LockTimeout:
            ex_dict = {}
            ex_dict.setdefault("message", "The action of restoring database is in process, please wait")
            self.finish(ex_dict)
            return 
        dict = {}
 #       dict.setdefault("code", '000000')
        dict.setdefault("message", "due to start cluster need a large of times, please wait to finished and email to you, when cluster have started!")
        
        self.finish(dict)
                
# cluster status. Return information about the cluster status.
#eq curl --user root:root "http://localhost:8888/cluster/check/online_node"
@require_basic_auth
class ClusterStatus(APIHandler):
    
    @asynchronous
    def get(self):
        try:
            zk_address = get_zk_address()
            zkoper_obj = ZkOpers(zk_address, 2181)
            existCluster = zkoper_obj.existCluster()

            cluster_status = zkoper_obj.retrieveClusterStatus()
            cluster_started_nodes = zkoper_obj.retrieve_started_nodes()
        except kazoo.exceptions.LockTimeout:
            raise HTTPAPIError(status_code=578, error_detail="lock by other thread",\
                                notification = "direct", \
                                log_message= "lock by other thread",\
                                response =  "current operation is using by other people, please wait a moment to try again!")
        dict = {}
 #       dict.setdefault("code", '000000')
        dict['message'] = cluster_status['_status']
        dict['nodelist'] = cluster_started_nodes
        
        self.finish(dict)
        zkoper_obj.close()

        
# stop mysqld service on every data node for entity cluster
# eg. curl --user root:root "http://localhost:8888/cluster/stop"
@require_basic_auth    
class ClusterStop(APIHandler):
    
    mysql_service_opers = Cluster_Mysql_Service_Opers()
    
    @asynchronous
    def get(self):
        try:
            self.mysql_service_opers.stop()
        except kazoo.exceptions.LockTimeout:
            raise HTTPAPIError(status_code=578, error_detail="lock by other thread",\
                                notification = "direct", \
                                log_message= "lock by other thread",\
                                response =  "current operation is using by other people, please wait a moment to try again!")
        
        status_dict = {}
        status_dict['_status'] = 'stopping'
        zk_address = get_zk_address()
        zkoper_obj = ZkOpers(zk_address, 2181)
        existCluster = zkoper_obj.existCluster()

        zkoper_obj.writeClusterStatus(status_dict)
        
        dict = {}
        #dict.setdefault("code", '000000')
        dict.setdefault("message", "due to stop cluster need a large of times, please wait to finished and email to you, when cluster have stoped!")
        
        self.finish(dict)
        
