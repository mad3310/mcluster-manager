#-*- coding: utf-8 -*-

'''
Created on 2013-7-21

@author: asus
'''
from base import APIHandler
from common.zkOpers import ZkOpers

# retrieve the status value of special monitor type, the monitor type include cluster,node,db.
# In different monitor type, there are many of monitor points. 
# eg. curl "http://localhost:8888/mcluster/status/{cluster,node,db}"         
class MclusterStatusDetail(APIHandler):
   
    def get(self, monitor_type):
        if monitor_type == None:
            raise "monitor type should be not null!"
        
        result = {}
        
        zkOper = ZkOpers()
        try:
            monitor_status_list = zkOper.retrieve_monitor_status_list(monitor_type)
        
            for monitor_status_key in monitor_status_list:
                monitor_status_value = zkOper.retrieve_monitor_status_value(monitor_type, monitor_status_key)
                result.setdefault(monitor_status_key, monitor_status_value)
            
        finally:
            zkOper.stop()
            
        self.finish(result)
            
            
            
# retrieve the status value of all monitor type 
# eg. curl "http://localhost:8888/mcluster/status"          
class MclusterStatus(APIHandler):
 
    def get(self):
        result = {}
        zkOper = ZkOpers()
        try: 
            monitor_types = zkOper.retrieve_monitor_type()
            
            for monitor_type in monitor_types:
                monitor_status_list = zkOper.retrieve_monitor_status_list(monitor_type)
            
                monitor_type_sub_dict = {}
                for monitor_status_key in monitor_status_list:
                    monitor_status_value = zkOper.retrieve_monitor_status_value(monitor_type, monitor_status_key)
                    monitor_type_sub_dict.setdefault(monitor_status_key, monitor_status_value)
                
                result.setdefault(monitor_type,monitor_type_sub_dict)
        finally:
            zkOper.stop()
            
        self.finish(result)
