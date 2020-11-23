import unittest
import tempfile
import os

from aiounittest import AsyncTestCase

from infinitd_server.db import Db
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig, MiscConfig
from infinitd_server.sse import SseQueues

import test_data

class TestDb(AsyncTestCase):
    def setUp(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        userQueues = SseQueues()
        bgQueues = SseQueues()
        battleCoordinator = BattleCoordinator(SseQueues())
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                battleCoordinator = battleCoordinator, dbPath=self.dbPath)

    def tearDown(self):
        os.remove(self.dbPath)

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

    def test_getUserSummaryByName(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        user = self.db.getUserSummaryByName("bob")

        self.assertIsNotNone(user)
        self.assertEqual(user.name, "bob") # pytype: disable=attribute-error

    def test_newUserNotInBattle(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        user = self.db.getUserSummaryByName("bob")

        self.assertIsNotNone(user)
        self.assertEqual(user.inBattle, False) # pytype: disable=attribute-error

    async def test_accumulateGold(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        self.assertTrue(self.db.register(uid="bar", name="sue"))
        # Sue shouldn't accumulate anything since she's in a battle.
        await self.db.setInBattle("sue", True)
        await self.db.setInBattle("bob", False)

        await self.db.accumulateGold()

        bob = self.db.getUserSummaryByName("bob")
        self.assertIsNotNone(bob)
        self.assertEqual(bob.gold, 101) # pytype: disable=attribute-error
        sue = self.db.getUserSummaryByName("sue")
        self.assertIsNotNone(sue)
        self.assertEqual(sue.gold, 100) # pytype: disable=attribute-error

if __name__ == "__main__":
    unittest.main()
