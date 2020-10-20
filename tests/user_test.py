import unittest

from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.game_config import ConfigId
from infinitdserver.user import MutableUser, User

class TestMutableUser(unittest.TestCase):
    def setUp(self):
        self.battleground = BattlegroundState(towers = BgTowersState.empty(5, 5))
        self.user = User(
                uid = "test_uid",
                name = "rofer",
                gold = 100,
                accumulatedGold = 200,
                goldPerMinute = 2,
                inBattle = False,
                wave = [],
                battleground = self.battleground,
                )
        self.mutableUser = MutableUser(self.user)

    def test_noChange(self):
        self.assertFalse(self.mutableUser.battlegroundModified)
        self.assertFalse(self.mutableUser.summaryModified)
        self.assertFalse(self.mutableUser.waveModified)

    def test_changedBack(self):
        self.mutableUser.battleground.towers.towers[1][1] = BgTowerState(0)
        self.mutableUser.battleground.towers.towers[1][1] = None
        self.mutableUser.gold = 102
        self.mutableUser.gold = 100
        self.mutableUser.wave.append(ConfigId(1))
        self.mutableUser.wave = []

        self.assertFalse(self.mutableUser.battlegroundModified)
        self.assertFalse(self.mutableUser.summaryModified)
        self.assertFalse(self.mutableUser.waveModified)

    def test_battlegroundModified(self):
        self.mutableUser.battleground.towers.towers[1][1] = BgTowerState(0)

        self.assertTrue(self.mutableUser.battlegroundModified)
        self.assertFalse(self.mutableUser.summaryModified)
        self.assertFalse(self.mutableUser.waveModified)

    def test_summaryModified(self):
        self.mutableUser.gold = 203

        self.assertFalse(self.mutableUser.battlegroundModified)
        self.assertTrue(self.mutableUser.summaryModified)
        self.assertFalse(self.mutableUser.waveModified)

    def test_waveModified(self):
        self.mutableUser.wave.append(ConfigId(2))

        self.assertFalse(self.mutableUser.battlegroundModified)
        self.assertTrue(self.mutableUser.summaryModified)
        self.assertTrue(self.mutableUser.waveModified)
