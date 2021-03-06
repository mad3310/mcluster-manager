# -*- coding: utf-8 -*-

'''
Created on 2013-7-21

@author: asus
'''

import logging
import time
import urllib
import tornado
import json
import sys
import re
import kazoo

from tornado.options import options
from tornado.httpclient import HTTPRequest

from common.configFileOpers import ConfigFileOpers
from common.zkOpers import ZkOpers
from common.abstract_mysql_service_opers import Abstract_Mysql_Service_Opers
from common.utils.exceptions import HTTPAPIError
from common.helper import _retrieve_userName_passwd
from common.helper import _request_fetch
from common.abstract_mysql_service_action_thread import Abstract_Mysql_Service_Action_Thread
from common.utils.exceptions import CommonException


class Cluster_Mysql_Service_Opers(Abstract_Mysql_Service_Opers):

    def __init__(self):
        '''
        Constructor
        '''

    '''
    @todo: arbitrator need to add one cluster_mode param?
    '''
    def start(self, cluster_flag, cluster_mode=None):
        # Start a thread to run the events
        cluster_start_action = Cluster_start_action(cluster_flag, cluster_mode)
        cluster_start_action.start()

    def stop(self):
        # Stop a thread to run the events
        cluster_stop_action = Cluster_stop_action()
        cluster_stop_action.start()


class PortStatus(object):
    def __init__(self):
        """
        constructor
        """

    def check_port(self, c_data_node_info_list):
        self.c_start_node_ip_list = []
        logging.info('/check/node_port/check start')
        online_count = 0
        url_post = "/inner/node_port/check"
        for data_node_ip in c_data_node_info_list:
            requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
            request = HTTPRequest(url=requesturi, method = 'GET')
            return_request = _request_fetch(request)
            if return_request == 'false':
                self.c_start_node_ip_list.append(data_node_ip)
#                 c_node_wsrep_status_dict.setdefault(data_node_ip, return_request)
        return self.c_start_node_ip_list


class WsrepStatus(object):
    def __init__(self):
        """
        constructor
        """
    def check_wsrep(self, w_data_node_info_list, w_node_wsrep_status_dict, node_num):
        logging.info('/inner/db/check/wsrep_status start')
        url_post = "/inner/db/check/wsrep_status"

        for data_node_ip in w_data_node_info_list:
            requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
            request = HTTPRequest(url=requesturi, method='GET')
            return_result = _request_fetch(request)
            w_node_wsrep_status_dict.setdefault(data_node_ip, return_result)

            logging.info('url_post is %s' %(url_post))

        wsrep_status_ok_count = 0
        for data_node_ip, return_result in w_node_wsrep_status_dict.iteritems():
            if "true" == return_result:
                wsrep_status_ok_count += 1

        return wsrep_status_ok_count


class StopIssue(object):

    def __init__(self):
        """
        constructor
        """

    def issue_stop(self, s_node_wsrep_status_dict, s_data_node_stop_finished_flag_dict, adminUser, adminPasswd):
        url_post = "/node/stop"
        logging.info('/node/stop start')
        for data_node_ip, return_result in s_node_wsrep_status_dict.iteritems():
            if "false" == return_result or not return_result:
                requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
                request = HTTPRequest(url=requesturi, method='GET',auth_username = adminUser, auth_password = adminPasswd)
                _request_fetch(request)
                stop_finished = self._check_stop_status(data_node_ip)
                s_data_node_stop_finished_flag_dict.setdefault(data_node_ip, stop_finished)

        logging.info("data node stop operation finished for start cluster, the stop statistic value is %s" % str(s_data_node_stop_finished_flag_dict))

    def _check_stop_status(self, data_node_ip):
        zkOper = ZkOpers()

        '''
        @todo: need to use lock to protect this process?
        '''
        stop_finished = False
        try:
            while not stop_finished:
                started_nodes = zkOper.retrieve_started_nodes()

                stop_finished = True
                for i in range(len(started_nodes)):
                    started_node = started_nodes[i]
                    if started_node == data_node_ip:
                        stop_finished = False

                time.sleep(1)
        finally:
            zkOper.stop()

        return stop_finished


class GaleraStatus(object):
    def __init__(self):
        """
        constructor
        """

    def check_status(self, c_data_node_stop_finished_flag_dict):
        self.c_uuid_seqno_dict = {}
        url_post = "/inner/db/recover/uuid_seqno"
        for (data_node_ip, stop_finished) in c_data_node_stop_finished_flag_dict.iteritems():
            if not stop_finished:
                self.c_uuid_seqno_dict.setdefault(data_node_ip, False)
                continue

            requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
            request = HTTPRequest(url=requesturi, method='GET')
            return_result = _request_fetch(request)
            uuid_seqno_json_value = json.loads(return_result)
            reponse_code = uuid_seqno_json_value['meta']['code']
            if reponse_code != 200:
                self.c_uuid_seqno_dict.setdefault(data_node_ip, False)
                continue
#                 status_dict['_status'] = 'failed'
#                 self.zkOper.writeClusterStatus(status_dict)
#                 error_message = "%s's uuid_seqno api no return right result!" % (data_node_ip)
#                 raise HTTPAPIError(status_code=500, error_detail= error_message,
#                                    notification = "direct",
#                                    log_message= error_message,
#                                    response =  error_message)
            uuid_seqno_sub_dict = {}
            uuid = uuid_seqno_json_value['response']['uuid']
            seqno_str = uuid_seqno_json_value['response']['seqno']
            if seqno_str == '':
                seqno = -1
            else:
                seqno = int(seqno_str)

            uuid_seqno_sub_dict.setdefault('uuid', uuid)
            uuid_seqno_sub_dict.setdefault('seqno', seqno)
            uuid_seqno_sub_dict.setdefault('node_ip', data_node_ip)
            logging.info("when sort the node's seqno, ip:%s,uuid:%s,seqno:%s" % (data_node_ip, uuid, str(seqno)))

            self.c_uuid_seqno_dict.setdefault(data_node_ip, uuid_seqno_sub_dict)

        logging.info("Before sort, the uuid_seqno_dict value is %s" % str(self.c_uuid_seqno_dict))
        return self.c_uuid_seqno_dict


class Arbitrator(object):
    '''
    @todo: Arbitrator class need to review
    '''
    confOpers = ConfigFileOpers()

    def __init__(self):
        '''
        Constructor
        '''

    def communicate(self, peer_ip, url):
        http_client = tornado.httpclient.HTTPClient()
        requesturi = "http://" + peer_ip+":"+str(options.port)+url
        try:
            response = http_client.fetch(requesturi)
        except tornado.httpclient.HTTPError as e:
            logging.error(str(e))
            http_client.close()
            return "error"
        logging.info(str(response.body))
        return response.body

    def get_ip(self, data_node_ip_list):
        ret_dict = self.confOpers.getValue(options.data_node_property, ['dataNodeName','dataNodeIp'])
        node_name = ret_dict['dataNodeName']
        obj = re.search("-n-2", node_name)
        if obj != None:
            return ret_dict['dataNodeIp']
        else:
            tem_ip_list = data_node_ip_list
            tem_ip_list.remove(ret_dict['dataNodeIp'])
            result = ""
            for ip in tem_ip_list:
                url_post = "/inner/arbitrator/ip"
                result = self.communicate(ip, url_post)
                if result != "false":
                    break
            return result


class Cluster_start_action(Abstract_Mysql_Service_Action_Thread):

    def __init__(self, cluster_flag, cluster_mode):
        super(Cluster_start_action, self).__init__()
        self.cluster_flag = cluster_flag
        self.cluster_mode = cluster_mode

        zkOper = self.retrieve_zkOper()
        try:
            self.isLock, lock = zkOper.lock_cluster_start_stop_action()
        except kazoo.exceptions.LockTimeout:
            logging.info("a thread is starting this cluster, give up this operation!")
            return

        if not self.isLock:
            raise CommonException('a thread is starting this cluster, give up this operation!')

        self.lock = lock

    def run(self):
        try:
            self._issue_start_action(self.cluster_flag, self.cluster_mode)
        except:
            self.threading_exception_queue.put(sys.exc_info())

    def _issue_start_action(self, cluster_flag, cluster_mode):
        node_wsrep_status_dict = {}
        data_node_started_flag_dict = {}
        need_start_node_ip_list = []
        arbitrator_node_ip = []
        status_dict = {}

        try:
            data_node_info_list = self.zkOper.retrieve_data_node_list()
            node_num = len(data_node_info_list)
            adminUser, adminPasswd = _retrieve_userName_passwd()

            if None != cluster_mode:
                mode_dict = {
                    "cluster_mode" : cluster_mode
                }
                self.zkOper.writeClusterMode(mode_dict)

            if cluster_flag == 'new':
                status_dict.setdefault("_status", "initializing")
                self.zkOper.writeClusterStatus(status_dict)
                portstatus_obj = PortStatus()
                need_start_node_ip_list = portstatus_obj.check_port(data_node_info_list)
                logging.info("need_start_node_ip_list:" + str(need_start_node_ip_list))

                if node_num - len(need_start_node_ip_list) != 1:
                    error_message = "data nodes's status is abnormal."
                    status_dict['_status'] = 'failed'
                    self.zkOper.writeClusterStatus(status_dict)
                    # logging.error("Some nodes's status are abnormal")
                    raise CommonException(error_message)

                '''
                @todo: for arbitrator mode? need this code?
                '''
                if cluster_mode == "asymmetric":
                    arbitrator_node = Arbitrator()
                    arbitrator_ip = arbitrator_node.get_ip(data_node_info_list)
                    arbitrator_node_ip.append(arbitrator_ip)
                    need_start_node_ip_list.remove(arbitrator_ip)

            else:
                wsrepstatus_obj = WsrepStatus()
                w_num = wsrepstatus_obj.check_wsrep(data_node_info_list, node_wsrep_status_dict, node_num)
                if w_num == node_num:
                    error_message = "all data node's status is ok. No need to start them."
                    raise CommonException(error_message)

                logging.info("Check the data node wsrep status for start cluster, the wsrep status value is %s" % str(node_wsrep_status_dict))

                data_node_stop_finished_flag_dict = {}

                stop_issue_obj = StopIssue()
                stop_finished_count = stop_issue_obj.issue_stop(node_wsrep_status_dict, data_node_stop_finished_flag_dict, adminUser, adminPasswd)
                if stop_finished_count == len(data_node_stop_finished_flag_dict):
                    status_dict['_status'] = 'stopped'
                    self.zkOper.writeClusterStatus(status_dict)
                    self._send_email("mcluster", " mysql service have been stopped in the cluster")

                logging.info('nodes stopping finished!')

                _galerastatus_obj = GaleraStatus()

                uuid_seqno_dict = _galerastatus_obj.check_status(data_node_stop_finished_flag_dict)
                err_node = ""
                for (node_ip, value) in uuid_seqno_dict.items():
                    if not value:
                        err_node.join(node_ip)

                if err_node != "":
                    error_message = "data node(%s) error, please check the status and start it by human." % (node_ip)
                    status_dict['_status'] = 'failed'
                    self.zkOper.writeClusterStatus(status_dict)
                    raise CommonException(error_message)

                need_start_node_ip_list = self._sort_seqno(uuid_seqno_dict)
                logging.info("After sort, the uuid_seqno_dict value is %s" % str(need_start_node_ip_list))

            url_post = "/node/start"
            logging.info("/node/start start issue!")
            logging.info("need_start_node_ip_list:" + str(need_start_node_ip_list))

            for data_node_ip in need_start_node_ip_list:
                started_nodes = self.zkOper.retrieve_started_nodes()
#                started_nodes_count = len(started_nodes)

                isNewCluster = False
                if len(started_nodes) == 0:
                    isNewCluster = True

                args_dict = {}
                args_dict.setdefault("isNewCluster", str(isNewCluster))

                requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
                request = HTTPRequest(url=requesturi, method='POST', body=urllib.urlencode(args_dict),
                                      auth_username = adminUser, auth_password = adminPasswd)

                _request_fetch(request, timeout=100)

                start_finished = self._check_start_status(data_node_ip, cluster_flag)
                logging.info('request from node/start is ' + str(start_finished))
                if start_finished == False:
                    status_dict['_status'] = 'failed'
                    self.zkOper.writeClusterStatus(status_dict)
                    error_message = "%s'database status is failed!" % (data_node_ip)
                    raise CommonException(error_message)

                logging.info("check started nodes ok!")
                data_node_started_flag_dict.setdefault(data_node_ip, start_finished)

                '''
                @todo: for arbitrator need this code?
                '''
                if cluster_mode == "asymmetric":
                    arbitrator_ip = arbitrator_node_ip[0]
                    url_post = "arbitrator/node/start"
                    requesturi = "http://%s:%s%s" %(arbitrator_ip, options.port,url_post)
                    request = HTTPRequest(url=requesturi, method='POST', body=urllib.urlencode(args_dict),
                                      auth_username = adminUser, auth_password = adminPasswd)
                    logging.info("issue " + requesturi)
                    return_result = _request_fetch(request)
                    if return_result  == False:
                        raise HTTPAPIError("Garbd arbitrator start failed", \
                        notification = "direct", \
                        log_message="garbd arbitrator start failed",
                        response = "garbd arbitrator start failed")
                    else:
                        self.zkOper.write_started_node(arbitrator_ip)

            cluster_started_nodes_list = self.zkOper.retrieve_started_nodes()
            nodes_online = len(cluster_started_nodes_list)

            logging.info("starts nodes" + str(nodes_online))
            if nodes_online == node_num:
                status_dict['_status'] = 'running'
                self._send_email("mcluster", " mysql services have been started in the cluster")
            else:
                status_dict['_status'] = 'failed'
                self._send_email("mcluster", " mysql services have benn started error")

            self.zkOper.writeClusterStatus(status_dict)
        except Exception, e:
            logging.error(e)
            status_dict['_status'] = 'failed'
            self.zkOper.writeClusterStatus(status_dict)
            raise e
        finally:
            if self.lock:
                self.zkOper.unLock_cluster_start_stop_action(self.lock)

            logging.info("Unlock cluster_start_stop_action done!")

    def _sort_seqno(self, param):
        uuid_unique_list = []
        seqno_list = []
        self.start_node_ip_list = []

        for (data_node_ip, uuid_seqno_sub_dict) in param.items():

            uuid = uuid_seqno_sub_dict.get('uuid')
            if '00000000-0000-0000-0000-000000000000' == uuid:
                self.start_node_ip_list.append(data_node_ip)
                continue

            uuid_unique_list.append(uuid)
            seqno_list.append(uuid_seqno_sub_dict.get('seqno'))

        uuid_unique_set = set(uuid_unique_list)
        if len(uuid_unique_set) != 1:
            error_message = "node's uuid_seqno api no return unique uuid!"
            raise CommonException(error_message)

        seqno_list.sort()

        logging.info("After seqno sort, the seqno_list value is %s" % str(seqno_list))

        for seqno in seqno_list:
            for (data_node_ip, uuid_seqno_sub_dict) in dict.items():
                seqno_target = uuid_seqno_sub_dict.get('seqno')
                if seqno == seqno_target:
                    self.start_node_ip_list.insert(0,data_node_ip)
                    del dict[data_node_ip]
                    break

        return self.start_node_ip_list

    def _check_start_status(self, data_node_ip, flag):

        start_finished = False
        sleep_t = options.sleep_time
        if flag == 'new':
            count = options.new_count_times
        else:
            count = options.old_count_times

        while not start_finished and count >= 0:
            started_nodes = self.zkOper.retrieve_started_nodes()
            count -= 1
            logging.info(str(data_node_ip) + "count down" + str(count))
            if data_node_ip in started_nodes:
                start_finished = True

            time.sleep(sleep_t)

        return start_finished


class Cluster_stop_action(Abstract_Mysql_Service_Action_Thread):

    def __init__(self):
        super(Cluster_stop_action, self).__init__()

        zkOper = self.retrieve_zkOper()
        try:
            self.isLock, lock = zkOper.lock_cluster_start_stop_action()
        except kazoo.exceptions.LockTimeout:
            logging.info("a thread is stopping this cluster, give up this operation!")
            return

        if not self.isLock:
            raise CommonException('a thread is stopping this cluster, give up this operation!')

        self.lock = lock

    def run(self):
        try:
            self._issue_stop_action()
        except:
            self.threading_exception_queue.put(sys.exc_info())

    def _issue_stop_action(self, lock):
        data_node_stop_finished_flag_dict = {}

        try:
            data_node_info_list = self.zkOper.retrieve_data_node_list()

            url_post = "/node/stop"

            adminUser, adminPasswd = _retrieve_userName_passwd()

            for i in range(len(data_node_info_list)):
                data_node_ip = data_node_info_list[i]

                requesturi = "http://%s:%s%s" % (data_node_ip, options.port, url_post)
                request = HTTPRequest(url=requesturi, method='GET', auth_username = adminUser, auth_password = adminPasswd)

                return_result = _request_fetch(request)

                stop_finished = self._check_stop_status(data_node_ip)

                data_node_stop_finished_flag_dict.setdefault(data_node_ip, stop_finished)

        finally:
            if self.lock is not None:
                self.zkOper.unLock_cluster_start_stop_action(self.lock)

        data_node_stop_finished_count = 0
        for data_node_ip, stop_finished in data_node_stop_finished_flag_dict.iteritems():
            if stop_finished:
                data_node_stop_finished_count += 1

        return data_node_stop_finished_count

    # duplicate Cluster_stop_action._check_stop_status
    def _check_stop_status(self, data_node_ip):

        '''
        @todo: need to lock this process?
        '''
        stop_finished = False
        while not stop_finished:
            started_nodes = self.zkOper.retrieve_started_nodes()

            stop_finished = True
            for i in range(len(started_nodes)):
                started_node = started_nodes[i]
                if started_node == data_node_ip:
                    stop_finished = False

            time.sleep(1)

        return stop_finished
