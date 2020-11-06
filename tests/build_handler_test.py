import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.game import Game
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitdserver.handler.build import BuildHandler
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger, MockLogger
import test_data

class TestBuildHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")

        return tornado.web.Application([
            (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler,
                dict(game=self.game))
            ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_successfulBuild(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/0/1", method="POST", body='{"towerId": 0}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 201)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[0][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 99) # pytype: disable=attribute-error

    def test_noBody(self):
        resp = self.fetch("/build/bob/0/1", method="POST", allow_nonstandard_methods=True)

        self.assertEqual(resp.code, 400)

    def test_wrongBody(self):
        resp = self.fetch("/build/bob/0/1", method="POST", body='{"wrongKey": 83}')

        self.assertEqual(resp.code, 400)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/phil/1/1", method="POST", body='{"towerId": 0}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/6/2", method="POST", body='{"towerId": 0}')
            resp2 = self.fetch("/build/bob/3/3", method="POST", body='{"towerId": 0}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(resp2.code, 404)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_insufficientGold(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/1/2", method="POST", body='{"towerId": 1}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_alreadyExists(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            # This should succeed
            resp = self.fetch("/build/bob/2/1", method="POST", body='{"towerId": 0}')
            # This should fail because there already is a tower there
            resp2 = self.fetch("/build/bob/2/1", method="POST", body='{"towerId": 2}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp2.code, 409)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[2][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
