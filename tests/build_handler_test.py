import unittest
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitdserver.db import Db
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, GameConfig, TowerConfig
from infinitdserver.handler.build import BuildHandler
from infinitdserver.sse import SseQueues

class TestBuildHandler(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        db_path = tmp_path
        playfieldConfig = PlayfieldConfig(
                numRows = 3,
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
                ]
        self.gameConfig = GameConfig(
                playfield = playfieldConfig,
                tiles = (),
                towers = towers,
                monsters = (),
                startingGold = 100,
                minGoldPerMinute = 1.0)
        userQueues = SseQueues()
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, db_path=db_path)
        self.db.register(uid="test_uid", name="bob")
        return tornado.web.Application([
            (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler,
                dict(db=self.db, gameConfig=self.gameConfig)),
            ])

    def test_successfulBuild(self):
        with unittest.mock.patch('infinitdserver.handler.base.BaseDbHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/build/bob/1/1", method="POST", body='{"towerId": 0}')

        self.assertEqual(resp.code, 201)
