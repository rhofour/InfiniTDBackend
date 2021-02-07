import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.game import Game
from infinitd_server.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitd_server.handler.sell import SellHandler
from infinitd_server.sse import SseQueues
from infinitd_server.logger import Logger, MockLogger
import test_data

class TestSellHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        _, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")
        self.initialBattleground = BattlegroundState.empty(self.gameConfig)
        self.initialBattleground.towers.towers[0][1] = BgTowerState(2)
        self.initialBattleground.towers.towers[1][2] = BgTowerState(1)
        asyncio.get_event_loop().run_until_complete(self.game.setBattleground("bob", self.initialBattleground))

        return tornado.web.Application([(r"/sell/(.*)", SellHandler, dict(game=self.game))])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_successfulSell(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [0], "cols": [1]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 200)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[1][2] = BgTowerState(1)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 101) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 101) # pytype: disable=attribute-error

    def test_successfulSellBoth(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [1, 0], "cols": [2, 1]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 200)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 151) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 151) # pytype: disable=attribute-error

    def test_wrongUser(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/phil", method="POST", body='{"rows": [1], "cols": [1]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [4], "cols": [2]}')
            resp2 = self.fetch("/sell/bob", method="POST", body='{"rows": [3], "cols": [3]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 400)
        self.assertEqual(resp2.code, 400)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [4], "cols": [2]}')
            resp2 = self.fetch("/sell/bob", method="POST", body='{"rows": [3], "cols": [3]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 400)
        self.assertEqual(resp2.code, 400)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error


    def test_noExistingTower(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [1], "cols": [1]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 400)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error
    
    def test_secondTowerOutOfBounds(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/sell/bob", method="POST", body='{"rows": [0, 3], "cols": [1, 3]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 400)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error
