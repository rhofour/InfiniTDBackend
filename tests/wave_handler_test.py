import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.db import Db
from infinitdserver.game_config import MonsterConfig
from infinitdserver.handler.wave import WaveHandler
from infinitdserver.sse import SseQueues
import test_data

class TestWaveHandlerPost(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
        self.gameConfig = test_data.gameConfig
        userQueues = SseQueues()
        bgQueues = SseQueues()
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                db_path=self.db_path)
        self.db.register(uid="test_uid", name="bob")
        return tornado.web.Application([
            (r"/wave/(.*)", WaveHandler,
                dict(db=self.db, gameConfig=self.gameConfig)),
            ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.db_path)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
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
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="POST", body='{"monsterId": 10}')

        self.assertEqual(resp.code, 400)

    def test_successfulPost(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="POST", body='{"monsterId": 0}')
        user = self.db.getUserByName("bob")

        self.assertEqual(resp.code, 201)
        self.assertListEqual(user.wave, [0])

class TestWaveHandlerDelete(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
        self.gameConfig = test_data.gameConfig
        userQueues = SseQueues()
        bgQueues = SseQueues()
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                db_path=self.db_path)
        self.db.register(uid="test_uid", name="bob")
        asyncio.get_event_loop().run_until_complete(self.db.addToWave("bob", 1))
        return tornado.web.Application([
            (r"/wave/(.*)", WaveHandler,
                dict(db=self.db, gameConfig=self.gameConfig)),
            ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.db_path)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/phil", method="DELETE")

        self.assertEqual(resp.code, 403)

    def test_successfulDelete(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/wave/bob", method="DELETE")
        user = self.db.getUserByName("bob")

        self.assertEqual(resp.code, 200)
        self.assertListEqual(user.wave, [])
