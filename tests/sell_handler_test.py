import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.game import Game
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitdserver.handler.sell import SellHandler
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger, MockLogger
import test_data

class TestSellHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")
        self.initialBattleground = BattlegroundState.empty(self.gameConfig)
        self.initialBattleground.towers.towers[0][1] = BgTowerState(2)
        self.initialBattleground.towers.towers[1][2] = BgTowerState(1)
        asyncio.get_event_loop().run_until_complete(self.game.setBattleground("bob", self.initialBattleground))

        return tornado.web.Application([(r"/sell/(.*)/([0-9]*)/([0-9]*)", SellHandler, dict(game=self.game))])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_successfulSell(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/sell/bob/0/1", method="DELETE")
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 200)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[1][2] = BgTowerState(1)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 101) # pytype: disable=attribute-error


    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/sell/phil/1/1", method="DELETE")
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, self.initialBattleground)

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/4/2", method="DELETE")
            resp2 = self.fetch("/build/bob/3/3", method="DELETE")
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(resp2.code, 404)
        self.assertEqual(battleground, self.initialBattleground)

    def test_noExistingTower(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/1/1", method="DELETE")
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(battleground, self.initialBattleground)
