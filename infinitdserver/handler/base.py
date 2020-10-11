from time import time
from typing import Optional, ClassVar

import firebase_admin.auth
import tornado.web

from infinitdserver.db import Db
from infinitdserver.logger import Logger

class BaseHandler(tornado.web.RequestHandler):
    startedTime: float
    logger: Logger
    requestId: int
    nextRequestId: ClassVar[int] = 0

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, authorization, content-type")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST, DELETE")

    def options(self, *args):
        pass

    def prepare(self):
        self.logger = Logger.getDefault()
        self.requestId = self.nextRequestId
        self.nextRequestId += 1

        self.logInfo("Started")

    def logInfo(self, msg: str, uid: Optional[str] = None):
        self.logger.info(self.__class__.__name__, self.requestId, msg, uid=uid)

    def on_finish(self):
        self.logInfo("Finished")

    def reply401(self):
        self.set_status(401)
        self.set_header("WWW-Authenticate", 'Bearer')
        raise tornado.web.Finish()

class BaseDbHandler(BaseHandler):
    db: Db

    def initialize(self, db):
        self.db = db

    def verifyAuthentication(self):
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                return firebase_admin.auth.verify_id_token(token)
            except Exception as e:
                print(f"Authorization error: {e}")
        self.reply401()
