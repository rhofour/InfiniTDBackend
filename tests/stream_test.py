import asyncio
import unittest
import tempfile
import os
import json

import cattr
import tornado
import tornado.testing

from infinitd_server.game import Game
from infinitd_server.logger import Logger, MockLogger
from infinitd_server.handler.stream import StreamHandler
import test_data

class TestWebSockets(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid1", name="bob")
        self.game.register(uid="test_uid2", name="sue")

        self.ws_url = "ws://localhost:" + str(self.get_http_port()) + "/stream"
        return tornado.web.Application([
            (r'/stream', StreamHandler, dict(game=self.game))
        ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    @tornado.testing.gen_test
    def test_receiveUpdates(self):
        ws_client = yield tornado.websocket.websocket_connect(self.ws_url)

        # Subscribe to update about bob
        ws_client.write_message("+user/bob")
        # Check we get the initial state
        initialBob = self.game.getUserSummaryByName("bob")
        response = yield ws_client.read_message()
        initialBobEncoded = json.dumps(cattr.unstructure(initialBob))
        self.assertEqual(response, f"user/bob/{initialBobEncoded}")

        # Modify bob to trigger an update
        with self.game.getMutableUserContext("test_uid1", "bob") as user:
            user.accumulatedGold = 5
        # Check for an update
        response = yield ws_client.read_message()

        bob = self.game.getUserSummaryByName("bob")
        bobEncoded = json.dumps(cattr.unstructure(bob))
        self.assertEqual(response, f"user/bob/{bobEncoded}")

    @tornado.testing.gen_test
    def test_receiveMixedUpdates(self):
        ws_client = yield tornado.websocket.websocket_connect(self.ws_url)

        # Subscribe to updates about bob
        ws_client.write_message("+user/bob")

        # Check we get the initial state
        initialBob = self.game.getUserSummaryByName("bob")
        response = yield ws_client.read_message()
        initialBobEncoded = json.dumps(cattr.unstructure(initialBob))
        self.assertEqual(response, f"user/bob/{initialBobEncoded}")

        # Subscribe to updates about sue
        ws_client.write_message("+user/sue")

        # Check we get the initial state
        initialSue = self.game.getUserSummaryByName("sue")
        response = yield ws_client.read_message()
        initialSueEncoded = json.dumps(cattr.unstructure(initialSue))
        self.assertEqual(response, f"user/sue/{initialSueEncoded}")

        # Modify bob to trigger an update
        with self.game.getMutableUserContext("test_uid1", "bob") as user:
            user.accumulatedGold = 5
        # Check for an update
        response = yield ws_client.read_message()
        bob = self.game.getUserSummaryByName("bob")
        bobEncoded = json.dumps(cattr.unstructure(bob))
        self.assertEqual(response, f"user/bob/{bobEncoded}")

        # Unsubscribe from sue
        ws_client.write_message("-user/sue")
        # Leave time for the unsubscribe to be handled
        yield asyncio.sleep(0.01)

        # Modify sue. We shouldn't receive this update
        with self.game.getMutableUserContext("test_uid2", "sue") as user:
            user.accumulatedGold = 7

        # Modify bob to trigger an another update
        with self.game.getMutableUserContext("test_uid1", "bob") as user:
            user.accumulatedGold = 9
        # Check for an update
        response = yield ws_client.read_message()
        bob = self.game.getUserSummaryByName("bob")
        bobEncoded = json.dumps(cattr.unstructure(bob))
        self.assertEqual(response, f"user/bob/{bobEncoded}")