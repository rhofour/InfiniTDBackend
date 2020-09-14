import unittest
from typing import List

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle import BattleComputer, BattleEvent, EventType, FpCellPos, FpRow, FpCol
from infinitdserver.game_config import ConfigId, CellPos, Row, Col
import test_data

class TestBattleComputer(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_emptyWave(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)

        results = battleComputer.computeBattle(battleground, [])

        self.assertListEqual(results, [])

    def test_oneMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
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

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

    def test_twoMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
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
            BattleEvent(
                type = EventType.MONSTER,
                id = 1,
                configId = 0,
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.5,
                endTime = 2.0,
                deleteAtEnd = True,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

    def test_oneMonsterOneCorner(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)
        expectedEvents: List[BattleEvent] = [
            BattleEvent(
                type = EventType.MONSTER,
                id = 0,
                configId = 0,
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(1)),
                startTime = 0.0,
                endTime = 0.5,
                deleteAtEnd = False,
            ),
            BattleEvent(
                type = EventType.MONSTER,
                id = 0,
                configId = 0,
                startPos = FpCellPos(FpRow(0), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
                deleteAtEnd = True,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

    def test_oneMonsterOneCornerLowRes(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        lowResBattleComputer = BattleComputer(
                gameConfig = test_data.gameConfig2row2col, gameTickSecs = 0.2)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])
        lowResResults = lowResBattleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, lowResResults)
