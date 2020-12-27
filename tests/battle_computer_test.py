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
import  InfiniTDFb.BattleEventsFb as BattleEventsFb
import test_data

EPSILON = 0.0001

class TestRandomBattlesRealConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # Use the real game config.
        gameConfigPath = Path('./game_config.json')
        with open(gameConfigPath) as gameConfigFile:
            gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
            self.gameConfig = GameConfig.fromGameConfigData(gameConfigData)

    @settings(deadline=500)
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
        self.assertEqual(results.fb._tab.Bytes, results2.fb._tab.Bytes)
        self.assertEqual(results.results, results2.results)

        # Ensure we can go from FB events to Python events and back.
        events = Battle.fbToEvents(results.fb.EventsNestedRoot())
        battle = Battle("random test battle", events, results.results)
        reencodedEventsFb = battle.encodeEventsFb()
        self.assertEqual(results.fb.EventsAsNumpy().tobytes(), reencodedEventsFb)

        # Check every ID is deleted by the end.
        activeIds = set()
        # Map every projectile fired to the tower it fired from.
        projFiredFrom: Dict[FpCellPos, List[MoveEvent]] = defaultdict(list)
        # pytype: disable=attribute-error
        for event in events:
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

    @given(st.data())
    def test_randomBattleCpp(self, data):
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
        results = battleComputer.computeBattle(battleground, wave, useCpp=True)
        results2 = battleComputer.computeBattle(battleground, wave, useCpp=True)

        # Ensure the process is deterministic.
        self.assertEqual(results.fb._tab.Bytes, results2.fb._tab.Bytes)
        self.assertEqual(results.results, results2.results)

        # Ensure we can go from FB events to Python events and back.
        events = Battle.fbToEvents(results.fb.EventsNestedRoot())
        battle = Battle("random test battle", events, results.results)
        # Something changes here, possibly because it's not a nested FB.
        reencodedEventsBytes = battle.encodeEventsFb()
        reencodedEventsFb = BattleEventsFb.BattleEventsFb.GetRootAsBattleEventsFb(reencodedEventsBytes, 0)
        remadeBattle = Battle("re-encoded battle", Battle.fbToEvents(reencodedEventsFb), results.results)
        tripleEncodedEventsBytes = remadeBattle.encodeEventsFb()
        # This should stay the same.
        self.assertEqual(reencodedEventsBytes, tripleEncodedEventsBytes)

        # Check every ID is deleted by the end.
        activeIds = set()
        # Map every projectile fired to the tower it fired from.
        projFiredFrom: Dict[FpCellPos, List[MoveEvent]] = defaultdict(list)
        # pytype: disable=attribute-error
        print(events)
        for event in events:
            if event.eventType == EventType.MOVE:
                activeIds.add(event.id)
                if event.objType == ObjectType.PROJECTILE:
                    projFiredFrom[event.startPos].append(event)
                # Ensure bounds of every move are within the playfield
                self.assertGreaterEqual(event.startPos.row, 0)
                self.assertGreaterEqual(event.startPos.col, 0)
                self.assertLessEqual(event.startPos.row, self.gameConfig.playfield.numRows - 1)
                self.assertLessEqual(event.startPos.col, self.gameConfig.playfield.numCols - 1)
                self.assertGreaterEqual(event.destPos.row, 0)
                self.assertGreaterEqual(event.destPos.col, 0)
                self.assertLessEqual(event.destPos.row, self.gameConfig.playfield.numRows - 1)
                self.assertLessEqual(event.destPos.col, self.gameConfig.playfield.numCols - 1)
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

        # Test encoding / decoding events.
        encodedEventsStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedEventsStr)
        encodedEventsFb = battle.encodeEventsFb()
        decodedEventsFb = Battle.decodeEventsFb(encodedEventsFb)

        self.assertEqual(battle.events, decodedEvents)
        self.assertEqual(battle.events, decodedEventsFb)

        # Test encoding / decoding results.
        encodedResultsFb = battle.encodeResultsFb()
        decodedResultsFb = BattleResults.decodeFb(encodedResultsFb)

        self.assertEqual(battle.results, decodedResultsFb)

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

        # Test encoding / decoding events.
        encodedEventsStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedEventsStr)
        encodedEventsFb = battle.encodeEventsFb()
        decodedEventsFb = Battle.decodeEventsFb(encodedEventsFb)

        self.assertEqual(battle.events, decodedEvents)
        self.assertEqual(battle.events, decodedEventsFb)

        # Test encoding / decoding results.
        encodedResultsFb = battle.encodeResultsFb()
        decodedResultsFb = BattleResults.decodeFb(encodedResultsFb)

        self.assertEqual(battle.results, decodedResultsFb)
