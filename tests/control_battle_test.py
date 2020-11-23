import asyncio
import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitd_server.game import Game
from infinitd_server.game_config import ConfigId
from infinitd_server.handler.control_battle import ControlBattleHandler
from infinitd_server.logger import Logger, MockLogger
import test_data

class TestControlBattleHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.game.getMutableUserContext("test_uid", "bob", waitOnAwaitable) as user:
            user.wave = [ConfigId(0)]

        return tornado.web.Application([
            (r"/controlBattle/(.*)", ControlBattleHandler, dict(game=self.game)) ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_successfulStart(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="POST", allow_nonstandard_methods=True)

        self.assertEqual(resp.code, 201)

    def test_successfulStop(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="POST", allow_nonstandard_methods=True)
        self.assertEqual(resp.code, 201)

        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="DELETE")
        self.assertEqual(resp.code, 204)

    def test_successfulRestart(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="POST", allow_nonstandard_methods=True)
        self.assertEqual(resp.code, 201)

        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="DELETE")
        self.assertEqual(resp.code, 204)

        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/controlBattle/bob", method="POST", allow_nonstandard_methods=True)
        self.assertEqual(resp.code, 201)
