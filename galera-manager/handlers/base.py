# -*- coding: utf-8 -*-

import logging
import traceback

from tornado.web import RequestHandler,HTTPError
from tornado import escape
from tornado.options import options

from common.utils.exceptions import HTTPAPIError, UserVisiableException
from common.utils.mail import send_email
from common.helper.version import __version__, __app__
from common.helper import get_localhost_ip
from common.zkOpers import Requests_ZkOpers, Watch_ZkOpers


class BaseHandler(RequestHandler):

    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("blogdemo_user")
        if not user_id:
            return None
        return self.db.get("SELECT * FROM authors WHERE id = %s", int(user_id))

    def get_all_arguments(self):
        request_param = {}
        args = self.request.arguments
        for key in args:
            request_param.setdefault(key, args[key][0])
        return request_param


class APIHandler(BaseHandler):

    zkOper = None

    def retrieve_zkOper(self):
        if None == self.zkOper:
            self.zkOper = Requests_ZkOpers()
        return self.zkOper

    def retrieve_watch_zkOper(self):
        if None == self.zkOper:
            self.zkOper = Watch_ZkOpers()
        return self.zkOper

    def finish(self, chunk=None, notification=None):
        if chunk is None:
            chunk = {}

        if self.request.connection.stream.closed():
            return

        if isinstance(chunk, dict):
            if 'error_code' not in chunk.keys():
                chunk = {"meta": {"code": 200}, "response": chunk}
            else:
                chunk = {"meta": {"code ": 401}, "response": chunk}
            if notification:
                chunk["notification"] = {"message": notification}
        if type(chunk) is str:
            pass
        callback = escape.utf8(self.get_argument("callback", None))
        if callback:
            self.set_header("Content-Type", "application/x-javascript")

            if isinstance(chunk, dict):
                chunk = escape.json_encode(chunk)

            self._write_buffer = [callback, "(", chunk, ")"] if chunk else []
            super(APIHandler, self).finish()
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            super(APIHandler, self).finish(chunk)

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages."""
        debug = self.settings.get("debug", False)
        try:
            exc_info = kwargs.pop('exc_info')
            e = exc_info[1]

            if isinstance(e, HTTPAPIError):
                pass
            elif isinstance(e, UserVisiableException):
                user_message = e.__str__()
                e = HTTPAPIError(417, error_detail=user_message)
                status_code = e.status_code
            elif isinstance(e, HTTPError):
                e = HTTPAPIError(e.status_code)
            else:
                e = HTTPAPIError(500)

            exception = "".join([ln for ln in traceback.format_exception(*exc_info)])

            if status_code == 500 and not debug:
                logging.error(e)
                self._send_error_email(exception)

            if debug:
                e.response["exception"] = exception

            self.clear()
            self.set_status(200)  # always return 200 OK for API errors
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.finish(str(e))
        except Exception:
            logging.error(traceback.format_exc())
            return super(APIHandler, self).write_error(status_code, **kwargs)

    def _send_error_email(self, exception):
        try:
            local_ip = get_localhost_ip()
            version_str = '{0}-{1}'.format(__app__, __version__)
            logging.info("version_str :" + str(version_str))
            # send email
            subject = "[%s]Internal Server Error " % options.sitename
            body = "{0}\n{1}\nip:{2}".format(exception, version_str, local_ip)

#            email_from = "%s <noreply@%s>" % (options.sitename, options.domain)
            if options.send_email_switch:
                send_email(options.admins, subject, body)
        except Exception:
            logging.error(traceback.format_exc())


class ErrorHandler(RequestHandler):
    """Default 404: Not Found handler."""
    def prepare(self):
        super(ErrorHandler, self).prepare()
        raise HTTPError(404)


class APIErrorHandler(APIHandler):
    """Default API 404: Not Found handler."""
    def prepare(self):
        super(APIErrorHandler, self).prepare()
        raise HTTPAPIError(404)
