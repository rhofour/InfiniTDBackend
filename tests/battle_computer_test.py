import unittest
from typing import List, NewType

import attr
import cattr
from enum import Enum, unique, auto

from infinitdserver.game_config import GameConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle import Battle, BattleComputer, BattleEvent, MoveEvent, DeleteEvent, ObjectType, EventType, FpCellPos, FpRow, FpCol
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
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.0,
                endTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

    def test_twoMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.0,
                endTime = 1.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.5,
                endTime = 2.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 2.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

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

        self.assertListEqual(results, expectedEvents)

    def test_oneMonsterOneCornerLowRes(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        lowResBattleComputer = BattleComputer(
                gameConfig = test_data.gameConfig2row2col, gameTickSecs = 0.2)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])
        lowResResults = lowResBattleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results, lowResResults)

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
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
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
                id = 1,
                startTime = 1.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(results, expectedEvents)

class TestBattleEventEncodingAndDecoding(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_oneMoveEvent(self):
        battle = Battle(
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
            ]
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)

    def test_twoEvents(self):
        battle = Battle(
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
            ]
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)

    def test_realCase1(self):
        gameConfig = GameConfig.from_json('{"playfield": {"numRows": 14, "numCols": 10, "monsterEnter": {"row": 0, "col": 0}, "monsterExit": {"row": 13, "col": 0}, "backgroundId": 0, "pathId": 1, "pathStartId": 2, "pathEndId": 3}, "tiles": [{"id": 0, "url": "static/CrappyGrass.png"}, {"id": 1, "url": "static/CrappyDirt.png"}, {"id": 2, "url": "static/CrappyStartDirt.png"}, {"id": 3, "url": "static/CrappyEndDirt.png"}], "towers": [{"id": 0, "url": "static/CrappyTowerSmall.png", "name": "Boring Tower", "cost": 1.0, "firingRate": 2.0, "range": 300.0, "damage": 5.0}, {"id": 1, "url": "static/CrappyTower.png", "name": "Better Tower", "cost": 5.0, "firingRate": 2.5, "range": 500.0, "damage": 15.0}], "monsters": [{"id": 0, "url": "static/GraySlime.png", "name": "Lame Slime", "health": 10.0, "speed": 2.0, "bounty": 1.0}, {"id": 1, "url": "static/GreenSlime.png", "name": "Green Slime", "health": 50.0, "speed": 2.0, "bounty": 6.0}, {"id": 2, "url": "static/YellowSlime.png", "name": "Yellow Slime", "health": 15.0, "speed": 5.0, "bounty": 5.0}], "misc": {"sellMultiplier": 0.8, "startingGold": 100, "minGoldPerMinute": 1.0, "fullWaveMultiplier": 2.0}}')
        battleComputer = BattleComputer(gameConfig = gameConfig)
        json_data = '{"towers": {"towers": [[null, null, null, null, null, {"id": 0}, null, null, null, null], [{"id": 0}, null, null, {"id": 0}, null, null, {"id": 0}, null, null, null], [null, {"id": 0}, null, null, {"id": 0}, null, null, null, null, null], [null, {"id": 0}, null, null, null, {"id": 0}, null, null, null, null], [{"id": 0}, null, null, {"id": 0}, null, null, null, null, null, null], [null, {"id": 0}, null, null, {"id": 0}, null, null, null, null, null], [null, {"id": 0}, null, null, null, {"id": 0}, null, null, null, null], [null, {"id": 0}, null, {"id": 0}, null, null, null, null, null, null], [null, {"id": 0}, null, null, {"id": 0}, null, null, null, null, null], [null, null, {"id": 0}, null, null, {"id": 0}, null, null, null, null], [null, null, null, {"id": 0}, null, null, null, null, null, null], [null, null, null, null, {"id": 0}, null, null, null, null, null], [null, null, null, null, null, {"id": 0}, null, null, null, null], [null, null, null, null, null, null, null, null, null, null]]}}'
        battleground = BattlegroundState.from_json(json_data)
        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

