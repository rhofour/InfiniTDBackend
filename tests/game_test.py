import unittest
import tempfile
import os
import asyncio

from aiounittest import AsyncTestCase

from infinitd_server.game import Game
from infinitd_server.logger import Logger, MockLogger

import test_data

class TestGame(AsyncTestCase):
    def setUp(self):
        Logger.setDefault(MockLogger())
        tmp_file, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

    def tearDown(self):
        os.remove(self.dbPath)
    
    async def test_calculateMissingBattlesNothingToDo(self):
        self.game.register(uid="bob_uid", name="bob")

        # This should do nothing as there's only one user with no wave.
        await self.game.calculateMissingBattles()

    async def test_calculateMissingBattles(self):
        self.game.register(uid="bob_uid", name="bob")
        self.game.register(uid="sue_uid", name="sue")
        self.game.register(uid="joe_uid", name="joe")
        # Make all the waves non-empty.
        with self.game.getMutableUserContext("bob_uid", "bob") as user:
            user.wave = [0]
        with self.game.getMutableUserContext("sue_uid", "sue") as user:
            user.wave = [0]
        with self.game.getMutableUserContext("joe_uid", "joe") as user:
            user.wave = [1]
        with self.game.getMutableUserContext("joe_uid", "joe") as user:
            user.goldPerMinuteOthers = 9.0 # To check if joe is updated or not.
        # Add fake battles.
        self.game._db.addTestBattle("sue_uid", "bob_uid", goldPerMinute=1.0)
        self.game._db.addTestBattle("bob_uid", "sue_uid", goldPerMinute=2.0)
        # Self battles should be ignored.
        self.game._db.addTestBattle("sue_uid", "sue_uid", goldPerMinute=1.0)
        self.game._db.addTestBattle("joe_uid", "sue_uid", goldPerMinute=3.0)

        await self.game.calculateMissingBattles()

        bob = self.game.getUserSummaryByName("bob")
        sue = self.game.getUserSummaryByName("sue")
        joe = self.game.getUserSummaryByName("joe")

        # Check the test battles still exist.
        self.assertIsNotNone(self.game.getBattle(sue, bob))
        self.assertIsNotNone(self.game.getBattle(bob, sue))
        self.assertIsNotNone(self.game.getBattle(sue, sue))
        self.assertIsNotNone(self.game.getBattle(joe, sue))

        # Check that new battles were created.
        self.assertIsNotNone(self.game.getBattle(bob, bob))
        self.assertIsNotNone(self.game.getBattle(sue, joe))
        self.assertIsNotNone(self.game.getBattle(joe, joe))

        # Check that goldPerSecondOthers was updated correctly.
        # Note these values are affected by the rival multiplier which is 0.5 here.
        self.assertEqual(bob.goldPerMinuteOthers, 0.5)
        self.assertEqual(sue.goldPerMinuteOthers, 2.5)
        # Joe receives this because the battle Sue vs. Joe will have a +1 participation bonus.
        self.assertEqual(joe.goldPerMinuteOthers, 0.5)