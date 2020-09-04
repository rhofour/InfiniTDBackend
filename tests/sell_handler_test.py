import asyncio
import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.db import Db
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitdserver.handler.sell import SellHandler
from infinitdserver.sse import SseQueues

class TestSellHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
        playfieldConfig = PlayfieldConfig(
                numRows = 4,
                numCols = 3,
                monsterEnter = CellPos(Row(0), Col(0)),
                monsterExit = CellPos(Row(2), Col(2)))
        towers = [
                TowerConfig(
                    id = 0,
                    url = "",
                    name = "Cheap Tower",
                    cost = 2,
                    firingRate = 1.0,
                    range = 10.0,
                    damage = 5.0),
                TowerConfig(
                    id = 1,
                    url = "",
                    name = "Expensive Tower",
                    cost = 101,
                    firingRate = 1.0,
                    range = 10.0,
                    damage = 5.0),
                ]
        self.gameConfig = GameConfig(
                playfield = playfieldConfig,
                tiles = (),
                towers = towers,
                monsters = (),
                misc = MiscConfig(
                    sellMultiplier = 0.5,
                    startingGold = 100,
                    minGoldPerMinute = 1.0
                ))
        userQueues = SseQueues()
        bgQueues = SseQueues()
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                db_path=self.db_path)
        self.db.register(uid="test_uid", name="bob")
        self.initialBattleground = BattlegroundState.empty(self.gameConfig)
        self.initialBattleground.towers.towers[0][1] = BgTowerState(0)
        self.initialBattleground.towers.towers[1][2] = BgTowerState(1)
        asyncio.get_event_loop().run_until_complete(self.db.setBattleground("bob", self.initialBattleground))
        return tornado.web.Application([
            (r"/sell/(.*)/([0-9]*)/([0-9]*)", SellHandler,
                dict(db=self.db, gameConfig=self.gameConfig)),
            ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.db_path)

    def test_successfulSell(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/sell/bob/0/1", method="DELETE")
        battleground = self.db.getBattleground("bob")
        user = self.db.getUserByName("bob")

        self.assertEqual(resp.code, 200)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[1][2] = BgTowerState(1)
        self.assertEqual(battleground, expectedBg)
        self.assertEqual(user.gold, 101)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/sell/phil/1/1", method="DELETE")
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp.code, 403)
        self.assertEqual(battleground, self.initialBattleground)

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/4/2", method="DELETE")
            resp2 = self.fetch("/build/bob/3/3", method="DELETE")
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(resp2.code, 404)
        self.assertEqual(battleground, self.initialBattleground)

    def test_noExistingTower(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/1/1", method="DELETE")
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(battleground, self.initialBattleground)
