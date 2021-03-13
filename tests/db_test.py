import unittest
import tempfile
import os
import asyncio

from aiounittest import AsyncTestCase

from infinitd_server.db import Db
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig, MiscConfig
from infinitd_server.sse import SseQueues
from infinitd_server.rivals import Rivals

import test_data

class TestDb(AsyncTestCase):
    def setUp(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        userQueues = SseQueues()
        bgQueues = SseQueues()
        rivalsQueues = SseQueues()
        battleCoordinator = BattleCoordinator(SseQueues())
        self.db = Db(gameConfig = self.gameConfig, userQueues = userQueues, bgQueues = bgQueues,
                battleCoordinator = battleCoordinator, rivalsQueues = rivalsQueues,
                dbPath=self.dbPath)

    def tearDown(self):
        os.remove(self.dbPath)

    def test_registerNewUser(self):
        self.db.register(uid="foo", name="bob")

    def test_registerSameUserFails(self):
        self.db.register(uid="foo", name="bob")
        # Test identical user
        with self.assertRaises(ValueError):
            self.db.register(uid="foo", name="bob")
        # Test identical name
        with self.assertRaises(ValueError):
            self.db.register(uid="bar", name="bob")
        # Test identical uid
        with self.assertRaises(ValueError):
            self.db.register(uid="foo", name="joe")

    def test_getUserSummaryByName(self):
        self.db.register(uid="foo", name="bob")

        user = self.db.getUserSummaryByName("bob")

        self.assertIsNotNone(user)
        self.assertEqual(user.name, "bob") # pytype: disable=attribute-error

    def test_newUserNotInBattle(self):
        self.db.register(uid="foo", name="bob")

        user = self.db.getUserSummaryByName("bob")

        self.assertIsNotNone(user)
        self.assertEqual(user.inBattle, False) # pytype: disable=attribute-error

    async def test_accumulateGold(self):
        self.db.register(uid="foo", name="bob")
        self.db.register(uid="bar", name="sue")
        # Sue shouldn't accumulate anything since she's in a battle.
        self.db.setInBattle("sue", True)
        self.db.setInBattle("bob", False)

        await self.db.accumulateGold()

        bob = self.db.getUserSummaryByName("bob")
        self.assertIsNotNone(bob)
        self.assertEqual(bob.gold, 101) # pytype: disable=attribute-error
        sue = self.db.getUserSummaryByName("sue")
        self.assertIsNotNone(sue)
        self.assertEqual(sue.gold, 100) # pytype: disable=attribute-error
    
    def test_getUserRivals(self):
        self.db.register(uid="foo", name="bob")
        self.db.register(uid="bar", name="sue")
        self.db.register(uid="baz", name="joe")
        with self.db.getMutableUserContext("foo") as user:
            user.accumulatedGold = 5
        with self.db.getMutableUserContext("bar") as user:
            user.accumulatedGold = 3
        with self.db.getMutableUserContext("baz") as user:
            user.accumulatedGold = 1
        
        bob_rivals = self.db.getUserRivals("bob")
        sue_rivals = self.db.getUserRivals("sue")
        joe_rivals = self.db.getUserRivals("joe")

        self.assertEqual(bob_rivals, Rivals([], ["sue"]))
        self.assertEqual(sue_rivals, Rivals(["bob"], ["joe"]))
        self.assertEqual(joe_rivals, Rivals(["sue"], []))
    
    def test_findMissingBattles(self):
        self.db.register(uid="bob_uid", name="bob")
        self.db.register(uid="sue_uid", name="sue")
        self.db.register(uid="joe_uid", name="joe")
        with self.db.getMutableUserContext("bob_uid") as user:
            user.accumulatedGold = 5
            user.wave = [0]
        with self.db.getMutableUserContext("sue_uid") as user:
            user.accumulatedGold = 3
            # No wave so there should be no battles where sue is attacking.
        with self.db.getMutableUserContext("joe_uid") as user:
            user.accumulatedGold = 1
            user.wave = [1]
        # Add fake battles.
        self.db.addTestBattle("bob_uid", "bob_uid")
        self.db.addTestBattle("joe_uid", "sue_uid")

        missingBattles = set(self.db.findMissingBattles())
        self.assertEqual(missingBattles, set([("bob_uid", "sue_uid"), ("joe_uid", "joe_uid")]))
    
    def test_updateGoldPerMinuteOthers(self):
        self.db.register(uid="bob_uid", name="bob")
        self.db.register(uid="sue_uid", name="sue")
        self.db.register(uid="joe_uid", name="joe")
        # Make all the waves non-empty.
        with self.db.getMutableUserContext("bob_uid") as user:
            user.wave = [0]
        with self.db.getMutableUserContext("sue_uid") as user:
            user.wave = [0]
        with self.db.getMutableUserContext("joe_uid") as user:
            user.wave = [1]
        with self.db.getMutableUserContext("joe_uid") as user:
            user.goldPerMinuteOthers = 9.0 # To check if joe is updated or not.
        # Add fake battles.
        self.db.addTestBattle("sue_uid", "bob_uid", goldPerMinute=1.0)
        self.db.addTestBattle("bob_uid", "sue_uid", goldPerMinute=2.0)
        # Self battles should be ignored.
        self.db.addTestBattle("sue_uid", "sue_uid", goldPerMinute=1.0)
        self.db.addTestBattle("joe_uid", "sue_uid", goldPerMinute=3.0)

        self.db.updateGoldPerMinuteOthers()

        # Note these values are affected by the rival multiplier which is 0.5 here.
        bob = self.db.getUserSummaryByName("bob")
        self.assertEqual(bob.goldPerMinuteOthers, 0.5)
        sue = self.db.getUserSummaryByName("sue")
        self.assertEqual(sue.goldPerMinuteOthers, 2.5)
        joe = self.db.getUserSummaryByName("joe")
        # No battles involve joe defending so they shouldn't be updated.
        self.assertEqual(joe.goldPerMinuteOthers, 9.0)

if __name__ == "__main__":
    unittest.main()
