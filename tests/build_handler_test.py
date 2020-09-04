import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.db import Db
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig, MiscConfig
from infinitdserver.handler.build import BuildHandler
from infinitdserver.sse import SseQueues

class TestBuildHandler(tornado.testing.AsyncHTTPTestCase):
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
                    cost = 1,
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
                TowerConfig(
                    id = 2,
                    url = "",
                    name = "Other Tower",
                    cost = 2,
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
        return tornado.web.Application([
            (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler,
                dict(db=self.db, gameConfig=self.gameConfig)),
            ])

    def tearDown(self):
        super().tearDown()
        os.remove(self.db_path)

    def test_successfulBuild(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/0/1", method="POST", body='{"towerId": 0}')
        battleground = self.db.getBattleground("bob")
        user = self.db.getUserByName("bob")

        self.assertEqual(resp.code, 201)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[0][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)
        self.assertEqual(user.gold, 99)

    def test_noBody(self):
        resp = self.fetch("/build/bob/0/1", method="POST", allow_nonstandard_methods=True)

        self.assertEqual(resp.code, 400)

    def test_wrongBody(self):
        resp = self.fetch("/build/bob/0/1", method="POST", body='{"wrongKey": 83}')

        self.assertEqual(resp.code, 400)

    def test_wrongUser(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/phil/1/1", method="POST", body='{"towerId": 0}')

        self.assertEqual(resp.code, 403)

    def test_outOfBounds(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/4/2", method="POST", body='{"towerId": 0}')
            resp2 = self.fetch("/build/bob/3/3", method="POST", body='{"towerId": 0}')
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp.code, 404)
        self.assertEqual(resp2.code, 404)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_insufficientGold(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/1/2", method="POST", body='{"towerId": 1}')
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp.code, 409)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    def test_alreadyExists(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            # This should succeed
            resp = self.fetch("/build/bob/2/1", method="POST", body='{"towerId": 0}')
            # This should fail because there already is a tower there
            resp2 = self.fetch("/build/bob/2/1", method="POST", body='{"towerId": 2}')
        battleground = self.db.getBattleground("bob")

        self.assertEqual(resp2.code, 409)
        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[2][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)