#! /usr/bin/env python
#-*- coding: utf-8 -*-
import os.path
import logging
# import logging
import logging.config
from tornado.options import options
from common.appdefine import mclusterManagerDefine

class debug_log():
    
    """
    classdoc
    """
    config_path = os.path.join(options.base_dir, "config")
    logging.config.fileConfig(config_path + '/logging.conf')
    
    def __init__(self, identifor = 'debug'):
        self.identifor = identifor
        
    def get_logger_object(self):
        _logger = logging.getLogger(self.identifor)
        _logger.setLevel(logging.INFO)
        return _logger

    
