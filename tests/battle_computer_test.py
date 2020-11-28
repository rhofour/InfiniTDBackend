import unittest
from collections import defaultdict
from typing import List, Tuple, Dict
from enum import Enum, unique, auto
from pathlib import Path
import json

import attr
import cattr
from hypothesis import given, assume, settings
import hypothesis.strategies as st


from infinitd_server.game_config import GameConfig, GameConfigData, CellPos, Row, Col, Url, MonsterConfig, ConfigId, TowerConfig
from infinitd_server.battleground_state import BattlegroundState, BgTowerState, TowerId
from infinitd_server.battle import Battle, BattleEvent, MoveEvent, DeleteEvent, DamageEvent, ObjectType, EventType, FpCellPos, FpRow, FpCol, BattleResults
from infinitd_server.battle_computer import BattleComputer, MonsterState, TowerState
from infinitd_server.game_config import ConfigId, CellPos, Row, Col
from infinitd_server.paths import pathExists
import test_data

EPSILON = 0.0001

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
        expectedBattleResults = BattleResults(
            monstersDefeated = {ConfigId(0): (0, 1)},
            bonuses = [ConfigId(0)],
            reward = 1,
            timeSecs = 2.51
        )
        self.assertEqual(expectedBattleResults, results.results)

    def test_oneMonsterOneShot(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        battleground.towers.towers[2][2] = BgTowerState(TowerId(1))
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.PROJECTILE,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(2.0), FpCol(2.0)),
                destPos = FpCellPos(FpRow(2.0), FpCol(0)),
                startTime = 0.0,
                endTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(5), FpCol(0)),
                startTime = 0.0,
                endTime = 2.5,
            ),
            DamageEvent(
                id = 0,
                startTime = 1.0,
                health = -5.0,
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
        expectedBattleResults = BattleResults(
            monstersDefeated = {ConfigId(0): (1, 1)},
            bonuses = [ConfigId(0), ConfigId(1)],
            reward = 22,
            timeSecs = 1.0
        )
        self.assertEqual(expectedBattleResults, results.results)

    def test_twoMonsterTwoShots(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        battleground.towers.towers[2][2] = BgTowerState(TowerId(1))
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.PROJECTILE,
                id = 2,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(2.0), FpCol(2.0)),
                destPos = FpCellPos(FpRow(2.0), FpCol(0.0)),
                startTime = 0.0,
                endTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0.0), FpCol(0.0)),
                destPos = FpCellPos(FpRow(5.0), FpCol(0.0)),
                startTime = 0.0,
                endTime = 2.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(2),
                startPos = FpCellPos(FpRow(0.0), FpCol(0.0)),
                destPos = FpCellPos(FpRow(5.0), FpCol(0.0)),
                startTime = 0.5,
                endTime = 5.5,
            ),
            DamageEvent(
                id = 0,
                startTime = 1.0,
                health = -5.0,
            ),
            DeleteEvent(
                objType = ObjectType.PROJECTILE,
                id = 2,
                startTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.PROJECTILE,
                id = 3,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(2.0), FpCol(2.0)),
                destPos = FpCellPos(FpRow(2.0), FpCol(0.0)),
                startTime = 1.50,
                endTime = 2.50,
            ),
            DamageEvent(
                id = 1,
                startTime = 2.50,
                health = 0.0,
            ),
            DeleteEvent(
                objType = ObjectType.PROJECTILE,
                id = 3,
                startTime = 2.50,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 2.50,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(2)])

        self.assertListEqual(expectedEvents, results.events)
        expectedBattleResults = BattleResults(
            monstersDefeated = {ConfigId(0): (1, 1), 2: (1, 1)},
            bonuses = [ConfigId(0), ConfigId(1)],
            reward = 32,
            timeSecs = 2.50
        )
        self.assertEqual(expectedBattleResults, results.results)

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

class TestRandomBattlesRealConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # Use the real game config.
        gameConfigPath = Path('./game_config.json')
        with open(gameConfigPath) as gameConfigFile:
            gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
            self.gameConfig = GameConfig.fromGameConfigData(gameConfigData)

    @settings(deadline=300)
    @given(st.data())
    def test_randomBattle(self, data):
        # Build the battleground
        # Generate a set of positions for tower locations.
        rows = st.integers(0, self.gameConfig.playfield.numRows - 1)
        cols = st.integers(0, self.gameConfig.playfield.numCols - 1)
        cellPos = st.tuples(rows, cols)
        towerPositions: List[Tuple[int, int]] = list(data.draw(st.sets(cellPos)))
        # Ensure this won't result in a blocked path.
        battleground = BattlegroundState.empty(self.gameConfig)
        for pos in towerPositions:
            battleground.towers.towers[pos[0]][pos[1]] = BgTowerState(TowerId(0))
        assume(pathExists(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit))
        # Generate an equal-sized list of valid tower IDs.
        possibleTowerIds = list(self.gameConfig.towers.keys())
        towerIndices = data.draw(st.lists(
            st.integers(0, len(possibleTowerIds)-1),
            min_size = len(towerPositions),
            max_size = len(towerPositions)))
        for (i, towerIdx) in enumerate(towerIndices):
            pos = towerPositions[i]
            battleground.towers.towers[pos[0]][pos[1]] = BgTowerState(
                TowerId(possibleTowerIds[towerIdx]))

        # Build the wave
        possibleMonsterIds = list(self.gameConfig.monsters.keys())
        monsterIndices = data.draw(st.lists(
            st.integers(0, len(possibleMonsterIds)-1),
            min_size=1))
        wave: List[ConfigId] = [possibleMonsterIds[i] for i in monsterIndices]

        battleComputer = BattleComputer(gameConfig = self.gameConfig)

        # First thing checked is that it doesn't throw an error.
        results = battleComputer.computeBattle(battleground, wave)
        results2 = battleComputer.computeBattle(battleground, wave)

        # Ensure the process is deterministic.
        self.assertEqual(results, results2)

        # Check every ID is deleted by the end.
        activeIds = set()
        # Map every projectile fired to the tower it fired from.
        projFiredFrom: Dict[FpCellPos, List[MoveEvent]] = defaultdict(list)
        # pytype: disable=attribute-error
        for event in results.events:
            if event.eventType == EventType.MOVE:
                activeIds.add(event.id)
                if event.objType == ObjectType.PROJECTILE:
                    projFiredFrom[event.startPos].append(event)
            if event.eventType == EventType.DELETE:
                activeIds.discard(event.id)
        # pytype: enable=attribute-error
        self.assertFalse(activeIds)

        for (firedFrom, events) in projFiredFrom.items():
            # Ensure projectiles are fired from grid cells.
            self.assertFalse(firedFrom.row % 1)
            self.assertFalse(firedFrom.col % 1)
            # Look up tower associated with this position.
            tower = battleground.towers.towers[int(firedFrom.row)][int(firedFrom.col)]
            self.assertTrue(tower)
            towerConfig = self.gameConfig.towers[tower.id]

            lastFired = -1000.0
            for event in events:
                # pytype: disable=attribute-error
                # Ensure tower isn't firing faster than its fire rate.
                timeBetweenFirings = event.startTime - lastFired
                self.assertGreaterEqual(
                        timeBetweenFirings, (1.0 / towerConfig.firingRate) - EPSILON)
                lastFired = event.startTime

                # Ensure the tower isn't firing farther than its range.
                firedDist = event.startPos.dist(event.destPos)
                self.assertLessEqual(firedDist, towerConfig.range + EPSILON)

                # Ensure the projectiles are traveling at the right speed.
                firedDuration = event.endTime - event.startTime
                projSpeed = firedDist / firedDuration
                self.assertAlmostEqual(towerConfig.projectileSpeed, projSpeed, places=3)

                # Check that projectile config ID matches.
                self.assertEqual(towerConfig.projectileId, event.configId)
                # pytype: enable=attribute-error

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
        encodedFb = battle.encodeEventsFb()
        decodedEventsFb = battle.decodeEventsFb(encodedFb)

        self.assertEqual(battle.events, decodedEvents)
        self.assertEqual(battle.events, decodedEventsFb)

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
        encodedFb = battle.encodeEventsFb()
        decodedEventsFb = battle.decodeEventsFb(encodedFb)

        self.assertEqual(battle.events, decodedEvents)
        self.assertEqual(battle.events, decodedEventsFb)
