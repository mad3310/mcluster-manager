# -*- coding: utf-8 -*-

import traceback

from tornado import escape

from backup_utils.base_backup_worker import BaseBackupWorker
from common.zkOpers import Requests_ZkOpers
from common.utils.exceptions import UserVisiableException


class BackupWorkerMethod(BaseBackupWorker):

    def __init__(self):
        BaseBackupWorker.__init__(self)
        self.zkOper = Requests_ZkOpers()

    def _get_usable_ips(self):
        online_node_list = self.zkOper.retrieve_started_nodes()
        if not online_node_list:
            raise UserVisiableException('not started node, please check zk node!')

        url_system_path = "/node/stat/workload"
        url_disk_path = "/node/stat/disk/available"
        url_memory_path = "/node/stat/memory/available"
        url_diskenough_path = "/node/stat/disk/enough"

        try:
            system_loads = self._retrieve_nodes_load(online_node_list, url_system_path)
            available_spaces = self._retrieve_nodes_load(online_node_list, url_disk_path)
            available_memory = self._retrieve_nodes_load(online_node_list, url_memory_path)
            disk_enough = self._retrieve_nodes_load(online_node_list, url_diskenough_path)

            usable_ips = self._analysis_usable_backup_node(system_loads, available_spaces, available_memory, disk_enough)

        except Exception, e:
            self.zkOper.write_backup_backup_info({'error': traceback.format_exc()})
            raise UserVisiableException(e)

        return usable_ips

    def _retrieve_nodes_load(self, online_node_list, url):
        response_message = self._dispatch_request_sync(online_node_list, 'GET', url)
        result = {}
        if response_message:
            for _info in response_message:
                if response_message[_info]["meta"]["code"] == 200:
                    last_message = response_message[_info]['response']
                    result.setdefault(_info, last_message)
        return result
