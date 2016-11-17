# -*- coding: utf-8 -*-

from MySQLdb import IntegrityError, ProgrammingError

from libs.db import db as mysql
from utils.command import InvokeCommand

from .consts import PT_COMMAND, PT_TEST_COMMAND


class SQLBatch(object):

    """
    批量执行SQL语句
    """

    def __init__(self, db_name):
        self.db_name = db_name

    @property
    def db(self):
        return mysql(self.db_name)

    def ddl_test(self, sqls, tb_name):
        """PT工具测试"""
        command = PT_TEST_COMMAND.format(sqls='"%s"' %sqls,
                                         db_name=self.db_name,
                                         tb_name=tb_name)
        return InvokeCommand.run_with_syn(command)

    def ddl(self, sqls, tb_name):
        """PT工具正式执行"""
        command = PT_COMMAND.format(sqls='"%s"' %sqls,
                                    db_name=self.db_name,
                                    tb_name=tb_name)
        return InvokeCommand.run_with_syn(command)

    def sql_excute(self,sql):
        error = ''
        try:
            self.db.execute(sql)
        except ProgrammingError, e:
            error = e[1]
        except IntegrityError, e:
            error = e[1]
        return error

    def dml(self, sqls):
        """执行失败需要回滚"""
        if not sqls:
            return None
        error = self.db.transaction(sqls)

        return error
