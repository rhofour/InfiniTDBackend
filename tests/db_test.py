import unittest
import tempfile
import os

from aiounittest import AsyncTestCase

from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig
from infinitdserver.sse import SseQueues

class TestDb(AsyncTestCase):
    def setUp(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
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
        bgQueues = SseQueues()
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                db_path=self.db_path)

    def tearDown(self):
        os.remove(self.db_path)

    def test_registerNewUser(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

    def test_registerSameUserFails(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        # Test identical user
        self.assertFalse(self.db.register(uid="foo", name="bob"))
        # Test identical name
        self.assertFalse(self.db.register(uid="bar", name="bob"))
        # Test identical uid
        self.assertFalse(self.db.register(uid="foo", name="joe"))

    def test_getUserByName(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        user = self.db.getUserByName("bob")

        self.assertEqual(user.name, "bob")

    def test_newUserNotInBattle(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        user = self.db.getUserByName("bob")

        self.assertEqual(user.inBattle, False)

    def test_getBattleground(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        battleground = self.db.getBattleground("bob")
        self.assertIsNone(self.db.getBattleground("unknown_username"))

        self.assertIs(type(battleground), BattlegroundState)
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    async def test_setInBattle(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        self.assertTrue(self.db.register(uid="bar", name="sue"))

        await self.db.setInBattle("sue", True)
        await self.db.setInBattle("bob", False)

        self.assertTrue(self.db.getUserByName("sue").inBattle)
        self.assertFalse(self.db.getUserByName("bob").inBattle)

    async def test_accumulateGold(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        self.assertTrue(self.db.register(uid="bar", name="sue"))
        # Sue shouldn't accumulate anything since she's in a battle.
        await self.db.setInBattle("sue", True)
        await self.db.setInBattle("bob", False)

        await self.db.accumulateGold()

        self.assertEqual(self.db.getUserByName("bob").gold, 101)
        self.assertEqual(self.db.getUserByName("sue").gold, 100)

    async def test_buildTowerWhileInBattle(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        await self.db.setInBattle("bob", True)

        with self.assertRaises(UserInBattleException):
            await self.db.buildTower(name="bob", row=0, col=1, towerId=0)

    async def test_buildTowerWithInsufficientGold(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        with self.assertRaises(UserHasInsufficientGoldException):
            await self.db.buildTower(name="bob", row=0, col=1, towerId=1)

    async def test_buildTowerSuccessfully(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        await self.db.buildTower(name="bob", row=0, col=1, towerId=0)
        battleground = self.db.getBattleground("bob")

        expectedBg = BattlegroundState.empty(self.gameConfig)
        expectedBg.towers.towers[0][1] = BgTowerState(0)
        self.assertEqual(battleground, expectedBg)

if __name__ == "__main__":
    unittest.main()
