import unittest
from typing import List, NewType
from enum import Enum, unique, auto

import attr
import cattr
from hypothesis import given
import hypothesis.strategies as st


from infinitdserver.game_config import GameConfig, CellPos, Row, Col, Url, MonsterConfig, ConfigId, TowerConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowerState, TowerId
from infinitdserver.battle import Battle, BattleEvent, MoveEvent, DeleteEvent, DamageEvent, ObjectType, EventType, FpCellPos, FpRow, FpCol, BattleResults
from infinitdserver.battle_computer import BattleComputer, MonsterState, TowerState
from infinitdserver.game_config import ConfigId, CellPos, Row, Col
import test_data

class TestBattleComputerEvents(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_emptyWave(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)

        with self.assertRaises(ValueError) as context:
            results = battleComputer.computeBattle(battleground, [])

    def test_oneMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(5), FpCol(0)),
                startTime = 0.0,
                endTime = 2.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 2.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(expectedEvents, results.events)

    def test_oneMonsterOneShot(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        battleground.towers.towers[2][2] = BgTowerState(TowerId(1))
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(5), FpCol(0)),
                startTime = 0.0,
                endTime = 2.5,
            ),
            MoveEvent(
                objType = ObjectType.PROJECTILE,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(2.0), FpCol(2.0)),
                destPos = FpCellPos(FpRow(2.0), FpCol(0)),
                startTime = 0.0,
                endTime = 1.0,
            ),
            DamageEvent(
                id = 0,
                startTime = 1.0,
                health = -10.0,
            ),
            DeleteEvent(
                objType = ObjectType.PROJECTILE,
                id = 1,
                startTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(expectedEvents, results.events)

    def test_twoMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(5), FpCol(0)),
                startTime = 0.0,
                endTime = 2.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(5), FpCol(0)),
                startTime = 0.5,
                endTime = 3.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 2.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 3.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(expectedEvents, results.events)

    def test_oneMonsterOneCorner(self):
        # Note which path the monster takes depends on the seed.
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(1), FpCol(0)),
                startTime = 0.0,
                endTime = 0.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(0)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(expectedEvents, results.events)

    def test_oneMonsterOneCornerLowRes(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        lowResBattleComputer = BattleComputer(
                gameConfig = test_data.gameConfig2row2col, gameTickSecs = 0.2)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])
        lowResResults = lowResBattleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results.events, lowResResults.events)

    def test_twoMonstersOneCorner(self):
        # Note which path each monster takes depends on the seed.
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col, seed=5)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(1)),
                startTime = 0.0,
                endTime = 0.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(1), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(0)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 1.0,
                endTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 1.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(expectedEvents, results.events)

class TestBattleEventEncodingAndDecoding(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_oneMoveEvent(self):
        battle = Battle(
            name = "testOneEvent",
            events = [
                MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    configId = ConfigId(0),
                    startPos = FpCellPos(FpRow(1), FpCol(0)),
                    destPos = FpCellPos(FpRow(0), FpCol(0)),
                    startTime = 1.0,
                    endTime = 1.5,
                ),
            ],
            results = BattleResults(
                monstersDefeated = {ConfigId(0): (0, 1)},
                bonuses = [],
                reward = 0.0,
                timeSecs = 1.5)
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)

    def test_twoEvents(self):
        battle = Battle(
            name = "testTwoEvents",
            events = [
                MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    configId = ConfigId(0),
                    startPos = FpCellPos(FpRow(1), FpCol(0)),
                    destPos = FpCellPos(FpRow(0), FpCol(0)),
                    startTime = 1.0,
                    endTime = 1.5,
                ),
                DeleteEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    startTime = 1.5,
                ),
            ],
            results = BattleResults(
                monstersDefeated = {ConfigId(0): (0, 1)},
                bonuses = [],
                reward = 0.0,
                timeSecs = 1.5)
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)
