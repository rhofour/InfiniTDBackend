import asyncio
from time import time
from typing import Optional, ClassVar, Awaitable, Callable, List, Dict

import firebase_admin.auth
import tornado.web
from tornado.ioloop import IOLoop

from infinitd_server.game import Game, UserMatchingError
from infinitd_server.db import MutableUserContext
from infinitd_server.logger import Logger

class BaseHandler(tornado.web.RequestHandler):
    logger: Logger
    game: Game
    requestId: int
    nextRequestId: ClassVar[int] = 0
    uid: Optional[str] = None

    def initialize(self, game):
        self.game = game

    def prepare(self):
        if self.request.method == "OPTIONS":
            return # Skip logging for options from CORS pre-flight requests.
        self.logger = Logger.getDefault()
        self.requestId = self.__class__.nextRequestId
        self.__class__.nextRequestId += 1

        self.logInfo("Started")

    def on_finish(self):
        if self.request.method == "OPTIONS":
            return # Skip logging for options from CORS pre-flight requests.
        self.logInfo("Finished")

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, authorization, content-type")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST, DELETE")

    def options(self, *args):
        pass

    def reply401(self):
        self.set_status(401) # Unauthorized
        self.set_header("WWW-Authenticate", 'Bearer')
        raise tornado.web.Finish()

    def verifyAuthentication(self) -> Optional[Dict]:
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                decodedToken = firebase_admin.auth.verify_id_token(token)
                if decodedToken["uid"]:
                    self.uid = decodedToken["uid"]
                return decodedToken
            except Exception as e:
                self.logWarn(f"Authorization error: {e}")
        self.reply401()

    def getMutableUser(self, expectedName: str) -> MutableUserContext:
        decodedToken = self.verifyAuthentication()
        uid = decodedToken["uid"]
        try:
            def addAwaitable(a: Awaitable[None]):
                async def awaitCallback():
                    await a
                IOLoop.current().add_callback(awaitCallback)
            return self.game.getMutableUserContext(uid = uid, expectedName = expectedName, addAwaitable = addAwaitable)
        except UserMatchingError as e:
            self.logWarn(str(e))
            self.set_status(403) # Forbidden
            raise tornado.web.Finish()
        except ValueError as e:
            self.logWarn(str(e))
            self.set_status(404) # Not found
            raise tornado.web.Finish()

    # Logging methods
    def logInfo(self, msg: str):
        self.logger.info(self.__class__.__name__, self.requestId, msg, uid=self.uid)

    def logWarn(self, msg: str):
        self.logger.warn(self.__class__.__name__, self.requestId, msg, uid=self.uid)

    def logError(self, msg: str):
        self.logger.error(self.__class__.__name__, self.requestId, msg, uid=self.uid)
