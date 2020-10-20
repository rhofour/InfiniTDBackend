import asyncio
from time import time
from typing import Optional, ClassVar, Awaitable, Callable, List

import firebase_admin.auth
import tornado.web
from tornado.ioloop import IOLoop

from infinitdserver.game import Game, UserMatchingError
from infinitdserver.db import MutableUserContext
from infinitdserver.logger import Logger

class BaseHandler(tornado.web.RequestHandler):
    logger: Logger
    game: Game
    requestId: int
    awaitables: List[Awaitable[None]]
    nextRequestId: ClassVar[int] = 0

    def initialize(self, game):
        self.game = game
        self.awaitables = []

    def prepare(self):
        self.logger = Logger.getDefault()
        self.requestId = self.__class__.nextRequestId
        self.__class__.nextRequestId += 1

        self.logInfo("Started")

    def on_finish(self):
        self.logInfo(f"Finished, awaiting {len(self.awaitables)} awaitables.")

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

    def verifyAuthentication(self):
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                return firebase_admin.auth.verify_id_token(token)
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
            self.logWarn(str(e), uid=uid)
            self.set_status(403) # Forbidden
            raise tornado.web.Finish()
        except ValueError as e:
            self.logWarn(str(e), uid=uid)
            self.set_status(404) # Not found
            raise tornado.web.Finish()

    # Logging methods
    def logInfo(self, msg: str, uid: Optional[str] = None):
        self.logger.info(self.__class__.__name__, self.requestId, msg, uid=uid)

    def logWarn(self, msg: str, uid: Optional[str] = None):
        self.logger.warn(self.__class__.__name__, self.requestId, msg, uid=uid)

    def logError(self, msg: str, uid: Optional[str] = None):
        self.logger.error(self.__class__.__name__, self.requestId, msg, uid=uid)
