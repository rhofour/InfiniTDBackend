import unittest
import tempfile
import os

from aiounittest import AsyncTestCase

from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig, MiscConfig
from infinitdserver.sse import SseQueues
import test_data

class TestDb(AsyncTestCase):
    def setUp(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
        self.gameConfig = test_data.gameConfig
        userQueues = SseQueues()
        bgQueues = SseQueues()
        battleCoordinator = BattleCoordinator(SseQueues())
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                battleCoordinator = battleCoordinator, db_path=self.db_path)

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

    async def test_buildTowerThatBlocksPath(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        with self.assertRaises(ValueError):
            await self.db.buildTower(name="bob", row=0, col=0, towerId=0)
        battleground = self.db.getBattleground("bob")

        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

    async def test_sellTowerWhileInBattle(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        initialBattleground = BattlegroundState.empty(self.gameConfig)
        initialBattleground.towers.towers[1][0] = BgTowerState(0)
        await self.db.setBattleground("bob", initialBattleground)
        await self.db.setInBattle("bob", True)

        with self.assertRaises(UserInBattleException):
            await self.db.sellTower(name="bob", row=1, col=0)

        battleground = self.db.getBattleground("bob")
        self.assertEqual(battleground, initialBattleground)

    async def test_sellTowerWhileNoneExists(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        with self.assertRaises(ValueError):
            await self.db.sellTower(name="bob", row=1, col=0)

    async def test_sellTowerSuccessfully(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        initialBattleground = BattlegroundState.empty(self.gameConfig)
        initialBattleground.towers.towers[1][0] = BgTowerState(1)
        await self.db.setBattleground("bob", initialBattleground)

        await self.db.sellTower(name="bob", row=1, col=0)

        user = self.db.getUserByName("bob")
        self.assertEqual(user.gold, 150)
        self.assertEqual(user.accumulatedGold, 150)
        battleground = self.db.getBattleground("bob")
        self.assertEqual(battleground, BattlegroundState.empty(self.gameConfig))

if __name__ == "__main__":
    unittest.main()
