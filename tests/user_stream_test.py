import asyncio
import unittest
import tempfile
import os
import json

import cattr
import tornado

from infinitd_server.game import Game
from infinitd_server.logger import Logger, MockLogger
from infinitd_server.user import FrozenUserSummary
from infinitd_server.handler.user_stream import UserStreamHandler
from sse_test_case import SseTestCase
import test_data

class TestUserStreamHandler(SseTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid1", name="bob")
        with self.game.getMutableUserContext("test_uid1", "bob") as user:
            user.accumulatedGold = 5
            user.goldPerMinuteSelf = 2

        return tornado.web.Application([ (r"/userStream/(.*)", UserStreamHandler, dict(game=self.game)) ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)
    
    def test_initalState(self):
        initialUser = self.game.getUserSummaryByName("bob") 

        def initial_user(x):
            user = cattr.structure(json.loads(x), FrozenUserSummary)
            self.assertEqual(initialUser, user)

        self.fetchSse(
            "/userStream/bob",
            expectations=[initial_user])
        self.wait(timeout=1.0)

    def test_update(self):
        initialUser = self.game.getUserSummaryByName("bob") 

        def initial_user(x):
            user = cattr.structure(json.loads(x), FrozenUserSummary)
            self.assertEqual(initialUser, user)

            # Update the user here
            async def waitOnAwaitable(x):
                await x
            with self.game.getMutableUserContext("test_uid1", "bob") as user:
                user.accumulatedGold = 7.0

        def updated_user(x):
            user = cattr.structure(json.loads(x), FrozenUserSummary)
            self.assertEqual(user.accumulatedGold, 7.0)

        self.fetchSse(
            "/userStream/bob",
            expectations=[initial_user, updated_user])
        self.wait(timeout=1.0)