import unittest
from typing import List

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle import BattleComputer, BattleEvent, EventType, FpCellPos, FpRow, FpCol
from infinitdserver.game_config import ConfigId
import test_data

class TestBattleComputer(unittest.TestCase):
    def setUp(self):
        self.gameConfig = test_data.gameConfig
        self.battleComputer = BattleComputer(gameConfig = self.gameConfig)

    def test_emptyWave(self):
        battleground = BattlegroundState.empty(self.gameConfig)

        results = self.battleComputer.computeBattle(battleground, [])

        self.assertListEqual(results, [])

    def test_oneMonsterNoTowers(self):
        battleground = BattlegroundState.empty(self.gameConfig)
        expectedEvents: List[BattleEvent] = [
            BattleEvent(
                type = EventType.MONSTER,
                id = 0,
                configId = 0,
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.0,
                endTime = 1.5,
                deleteAtEnd = True,
            ),
        ]

        results = self.battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, expectedEvents)
