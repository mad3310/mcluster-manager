# -*- coding: utf-8 -*-
from __future__ import absolute_import

from utils.storify import storify


# -----------------------------------
# 普通常量
# 注意:1、包括枚举、字符串，数字常量等
#     2、推荐名称见名知意，否则明确注释
# -----------------------------------
MONITOR_TYPE = {'db': ['existed_db_anti_item',
                       'wsrep_status',
                       'cur_user_conns',
                       'cur_conns',
                       'write_read_avaliable'
                       ],

                'node': ['log_health',
                         'log_error',
                         'started'
                         ]
                }

# 数据库节点监控类型
DB_MONITOR_TYPE = storify(dict(
    EXISTED_DB_ANTI_ITEM='existed_db_anti_item',
    WSREP_STATUS='wsrep_status',
    CUR_USER_CONNS='cur_user_conns',
    CUR_CONNS='cur_conns',
    WRITE_REAL_AVALLIABLE='write_read_avaliable'
))

# 容器节点监控类型
NODE_MONITOR_TYPE = storify(dict(
    LOG_HEALTH='health',
    LOG_ERROR='log_error',
    STARTED='started'
))


# 监控警告等级
ALARM_LEVEL = storify(dict(
    SERIOUS='tel:sms:email',
    GENERAL='sms:email',
    NOTHING='nothing'
))


# -----------------------------
# 路径字符串常量
# 注意:尽量添加注释表明文件夹下内容
# -----------------------------
MCLUSTER_MYSQL_DIR = '/srv/mcluster/mysql'


# ---------------------------------------------
# Shell字符串常量
# 注意:1、推荐定义通用的shell字符串，保证各模块公用
#     2、特殊的shell字符串，注意添加注释表明含义
# --------------------------------------------
DU_S = 'du -s %s'
