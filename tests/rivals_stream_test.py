import asyncio
import unittest
import tempfile
import os
import json

import tornado.testing
import cattr

from infinitd_server.game import Game
from infinitd_server.logger import Logger, MockLogger
from infinitd_server.rivals import Rivals
from infinitd_server.handler.rivals_stream import RivalsStreamHandler
from sse_test_case import SseTestCase
import test_data

class TestRivalsStreamHandler(SseTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid1", name="bob")
        self.game.register(uid="test_uid2", name="sam")
        self.game.register(uid="test_uid3", name="joe")
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.game.getMutableUserContext("test_uid1", "bob", waitOnAwaitable) as user:
            user.accumulatedGold = 5
            user.goldPerMinuteSelf = 2
        with self.game.getMutableUserContext("test_uid2", "sam", waitOnAwaitable) as user:
            user.accumulatedGold = 3
            user.goldPerMinuteSelf = 1
        with self.game.getMutableUserContext("test_uid3", "joe", waitOnAwaitable) as user:
            user.accumulatedGold = 2
            user.goldPerMinuteSelf = 3

        return tornado.web.Application([ (r"/rivalsStream/(.*)", RivalsStreamHandler, dict(game=self.game)) ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)
    
    def test_initalState(self):
        def initial_rivals(x):
            rivals = cattr.structure(json.loads(x), Rivals)
            self.assertEqual(Rivals(["bob"], ["joe"]), rivals)

        self.fetchSse(
            "/rivalsStream/sam",
            expectations=[initial_rivals])
        self.wait(timeout=1.0)

    def test_initalStateAfterAccumulate(self):
        def initial_rivals(x):
            rivals = cattr.structure(json.loads(x), Rivals)
            self.assertEqual(Rivals(["joe"], []), rivals)

        asyncio.get_event_loop().run_until_complete(self.game.accumulateGold())
        self.fetchSse(
            "/rivalsStream/sam",
            expectations=[initial_rivals])
        self.wait(timeout=1.0)

    def test_updateFromBelow(self):
        def initial_rivals(x):
            rivals = cattr.structure(json.loads(x), Rivals)
            self.assertEqual(Rivals([], ["sam"]), rivals)

            # Accumulate gold to trigger the next call
            asyncio.create_task(self.game.accumulateGold())
        def updated_rivals(x):
            rivals = cattr.structure(json.loads(x), Rivals)
            self.assertEqual(Rivals([], ["joe"]), rivals)

        self.fetchSse(
            "/rivalsStream/bob",
            expectations=[initial_rivals, updated_rivals])
        self.wait(timeout=1.0)