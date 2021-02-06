import asyncio
import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.game import Game
from infinitd_server.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitd_server.handler.build import BuildHandler
from infinitd_server.sse import SseQueues
from infinitd_server.logger import Logger, MockLogger
import test_data

class TestBuildHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        tmpFile, tmpPath = tempfile.mkstemp()
        self.dbPath = tmpPath
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")

        return tornado.web.Application([ (r"/build/(.*)", BuildHandler, dict(game=self.game)) ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)

    def test_successfulBuild1(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [0], "cols": [1], "towerIds": [0]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 201)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[0][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 99) # pytype: disable=attribute-error

    def test_successfulBuild3(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [0,1,2], "cols": [1,1,1], "towerIds": [0,0,0]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 201)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[0][1] = BgTowerState(0)
        expectedBg.towers.towers[1][1] = BgTowerState(0)
        expectedBg.towers.towers[2][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 97) # pytype: disable=attribute-error

    def test_noBody(self):
        resp = self.fetch("/build/bob", method="POST", allow_nonstandard_methods=True)

        self.assertEqual(resp.code, 400)

    def test_wrongBody(self):
        resp = self.fetch("/build/bob", method="POST", body='{"wrongKey": 83}')

        self.assertEqual(resp.code, 400)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/phil",
                method="POST",
                body='{"rows": [1], "cols": [1], "towerIds": [0]}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [6], "cols": [2], "towerIds": [0]}')
            resp2 = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [3], "cols": [3], "towerIds": [0]}')
        battleground = self.game.getBattleground("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(resp2.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_insufficientGold(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [1], "cols": [2], "towerIds": [1]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))
        self.assertEqual(user.gold, 100)

    def test_insufficientGoldMultiple(self):
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.game.getMutableUserContext("test_uid", "bob", waitOnAwaitable) as user:
            user.gold = 2

        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [1,2,3], "cols": [1,1,1], "towerIds": [0,0,0]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))
        self.assertEqual(user.gold, 2)

    def test_alreadyExists(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            # This should succeed
            self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [2], "cols": [1], "towerIds": [0]}')
            # This should fail because there already is a tower there
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [2], "cols": [1], "towerIds": [2]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[2][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 99) # pytype: disable=attribute-error

    def test_alreadyExistsInRequest(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            # This should fail because we're trying to build the same tower twice in one request.
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [2,2], "cols": [1,1], "towerIds": [0,2]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error

    def test_blocksPath(self):
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.game.getMutableUserContext("test_uid", "bob", waitOnAwaitable) as user:
            user.battleground.towers.towers[1][0] = BgTowerState(0)
            expectedBattleground = user.battleground
            expectedGold = user.gold

        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [0], "cols": [1], "towerIds": [0]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, expectedBattleground)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, expectedGold) # pytype: disable=attribute-error

    def test_blocksPathMultiple(self):
        initialUser = self.game.getUserSummaryByName("bob")
        expectedBattleground = self.game.getBattleground("bob")
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch(
                "/build/bob",
                method="POST",
                body='{"rows": [1, 0], "cols": [0, 1], "towerIds": [0, 0]}')
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, expectedBattleground)
        self.assertIsNotNone(user)
        self.assertEqual(user.gold, initialUser.gold) # pytype: disable=attribute-error
