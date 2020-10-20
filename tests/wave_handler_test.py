import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.game import Game
from infinitdserver.game_config import MonsterConfig
from infinitdserver.handler.wave import WaveHandler
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger, MockLogger
import test_data

class TestWaveHandlerPost(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath=self.dbPath)

        self.game.register(uid="test_uid", name="bob")

        return tornado.web.Application([(r"/wave/(.*)", WaveHandler, dict(game=self.game))])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/phil", method="POST", body='{"monsterId": 0}')

        self.assertEqual(resp.code, 403)

    def test_noBody(self):
        resp = self.fetch("/wave/bob", method="POST", allow_nonstandard_methods=True)

        self.assertEqual(resp.code, 400)

    def test_wrongBody(self):
        resp = self.fetch("/wave/bob", method="POST", body='{"wrongKey": 32}')

        self.assertEqual(resp.code, 400)

    def test_unknownMonster(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="POST", body='{"monsterId": 10}')

        self.assertEqual(resp.code, 400)

    def test_successfulPost(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="POST", body='{"monsterId": 0}')
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 201)
        self.assertIsNotNone(user)
        self.assertListEqual(user.wave, [0]) # pytype: disable=attribute-error

class TestWaveHandlerDelete(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath=self.dbPath)

        self.game.register(uid="test_uid", name="bob")
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.game.getMutableUserContext("test_uid", "bob", waitOnAwaitable) as user:
            self.game.addToWave(user, 1)

        return tornado.web.Application([(r"/wave/(.*)", WaveHandler, dict(game=self.game))])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/phil", method="DELETE")

        self.assertEqual(resp.code, 403)

    def test_successfulDelete(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="DELETE")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 200)
        self.assertIsNotNone(user)
        self.assertListEqual(user.wave, []) # pytype: disable=attribute-error

