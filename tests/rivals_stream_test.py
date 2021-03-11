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
import test_data

class TestRivalsStreamHandler(tornado.testing.AsyncHTTPTestCase):
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
    
    def fetchSse(self, url, expectations):
        callback_calls = 0
        def callback(x):
            nonlocal callback_calls
            self.assertEqual(x[:6], b"data: ")
            expectations[callback_calls](x[6:])
            callback_calls += 1
            if len(expectations) == callback_calls:
                self.stop()

        self.http_client.fetch(
            self.get_url(url),
            streaming_callback=callback)
    
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