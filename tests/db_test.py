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
        await self.db.setInBattle("sue", True)
        await self.db.setInBattle("bob", False)

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
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.db.getMutableUserContext("foo", waitOnAwaitable) as user:
            user.accumulatedGold = 5
        with self.db.getMutableUserContext("bar", waitOnAwaitable) as user:
            user.accumulatedGold = 3
        with self.db.getMutableUserContext("baz", waitOnAwaitable) as user:
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
        def waitOnAwaitable(x):
            asyncio.get_event_loop().run_until_complete(x)
        with self.db.getMutableUserContext("bob_uid", waitOnAwaitable) as user:
            user.accumulatedGold = 5
            user.wave = [0]
        with self.db.getMutableUserContext("sue_uid", waitOnAwaitable) as user:
            user.accumulatedGold = 3
            # No wave so there should be no battles where sue is attacking.
        with self.db.getMutableUserContext("joe_uid", waitOnAwaitable) as user:
            user.accumulatedGold = 1
            user.wave = [1]
        # Add fake battles.
        self.db.addTestBattle("bob_uid", "bob_uid")
        self.db.addTestBattle("joe_uid", "sue_uid")

        missingBattles = set(self.db.findMissingBattles())
        self.assertEqual(missingBattles, set([("bob_uid", "sue_uid"), ("joe_uid", "joe_uid")]))

if __name__ == "__main__":
    unittest.main()
