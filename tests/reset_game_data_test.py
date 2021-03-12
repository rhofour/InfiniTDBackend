import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitd_server.handler.admin.reset_game import ResetGameHandler
from infinitd_server.logger import Logger, MockLogger
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.game import Game
from infinitd_server.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
import test_data

class TestResetGameData(tornado.testing.AsyncHTTPTestCase):
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

        with self.game.getMutableUserContext("test_uid", "bob") as user:
            # These must be set separately or they cause gold per minute to be reset.
            user.wave = [0, 1, 0]
            user.battleground = self.initialBattleground
        with self.game.getMutableUserContext("test_uid", "bob") as user:
            user.gold = 50
            user.accumulatedGold = 110
            user.goldPerMinuteSelf = 2.5
            user.goldPerMinuteOthers = 1.5
            user.inBattle = True # So we can calculate a battle

        user = self.game.getUserSummaryByName("bob")
        def waitOnAwaitable(x):
            return asyncio.get_event_loop().run_until_complete(x)
        self.initialBattle = waitOnAwaitable(
            self.game.getOrMakeRecordedBattle("bob", "bob", "TestResetGameData", 0))

        self.game.register(uid="admin_uid", name="joe", admin=True)

        return tornado.web.Application([(r"/admin/resetGame", ResetGameHandler, dict(game=self.game))])
    
    def test_successfulReset(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "admin_uid"
            resp = self.fetch("/admin/resetGame", method="POST", allow_nonstandard_methods=True)
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")
        battle = self.game.getBattle(user, user)

        self.assertEqual(resp.code, 200)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        self.assertEqual(battleground, expectedBg)
        self.assertEqual(user.gold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 100) # pytype: disable=attribute-error
        self.assertEqual(user.goldPerMinuteSelf, 1.0) # pytype: disable=attribute-error
        self.assertEqual(user.goldPerMinuteOthers, 0) # pytype: disable=attribute-error
        self.assertEqual(user.wave, []) # pytype: disable=attribute-error
        self.assertFalse(user.inBattle)
        self.assertIsNone(battle)

    def test_nonAdminForbidden(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = "test_uid"
            resp = self.fetch("/admin/resetGame", method="POST", allow_nonstandard_methods=True)
        battleground = self.game.getBattleground("bob")
        user = self.game.getUserSummaryByName("bob")
        battle = self.game.getBattle(user, user)

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, self.initialBattleground)
        self.assertEqual(user.gold, 50) # pytype: disable=attribute-error
        self.assertEqual(user.accumulatedGold, 110) # pytype: disable=attribute-error
        self.assertEqual(user.goldPerMinuteSelf, 2.5) # pytype: disable=attribute-error
        self.assertEqual(user.goldPerMinuteOthers, 1.5) # pytype: disable=attribute-error
        self.assertEqual(user.wave, [0, 1, 0]) # pytype: disable=attribute-error
        self.assertTrue(user.inBattle)
        self.assertEqual(battle, self.initialBattle)

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)