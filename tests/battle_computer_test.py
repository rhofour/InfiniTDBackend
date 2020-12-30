import unittest
from collections import defaultdict
from typing import List, Tuple, Dict, Optional
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
import InfiniTDFb.BattleEventsFb as BattleEventsFb
import InfiniTDFb.MonstersDefeatedFb as MonstersDefeatedFb
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
        print("Wave: ", wave)

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
        # Map events to the objects they're affecting
        movesById: Dict[int, List[MoveEvent]] = defaultdict(list)
        damageById: Dict[int, List[DamageEvent]] = defaultdict(list)
        deleteById: Dict[int, DeleteEvent] = {}
        # Map every ID to the associated config ID
        idToConfigId: Dict[int, int] = {}
        # Map every ID to the associated object type
        idToObjType: Dict[int, ObjectType] = {}
        # pytype: disable=attribute-error
        lastSpawnedMoveEvent: Optional[MoveEvent] = None
        spawnFp = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        exitFp = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterExit)
        lastStartTime = 0.0
        # Ensure the first event is a move event starting at 0.0.
        firstEvent = events[0]
        self.assertEqual(firstEvent.eventType, EventType.MOVE)
        self.assertEqual(firstEvent.startTime, 0.0)
        enemiesDefeated = 0
        for event in events:
            # Ensure events are in sorted order.
            self.assertGreaterEqual(event.startTime, lastStartTime, msg="Events are not sorted.")
            lastStartTime = event.startTime
            if event.eventType == EventType.MOVE:
                activeIds.add(event.id)
                if event.objType == ObjectType.PROJECTILE:
                    projFiredFrom[event.startPos].append(event)
                movesById[event.id].append(event)
                if event.id in idToConfigId:
                    self.assertEqual(event.configId, idToConfigId[event.id])
                idToConfigId[event.id] = event.configId
                idToObjType[event.id] = event.objType
                # Ensure bounds of every move are within the playfield.
                self.assertGreaterEqual(event.startPos.row, 0)
                self.assertGreaterEqual(event.startPos.col, 0)
                self.assertLessEqual(event.startPos.row, self.gameConfig.playfield.numRows - 1)
                self.assertLessEqual(event.startPos.col, self.gameConfig.playfield.numCols - 1)
                self.assertGreaterEqual(event.destPos.row, 0)
                self.assertGreaterEqual(event.destPos.col, 0)
                self.assertLessEqual(event.destPos.row, self.gameConfig.playfield.numRows - 1)
                self.assertLessEqual(event.destPos.col, self.gameConfig.playfield.numCols - 1)
                # Ensure monsters are traveling at the correct speed.
                if event.objType == ObjectType.MONSTER:
                    dist: float = event.startPos.dist(event.destPos)
                    time: float = event.endTime - event.startTime
                    expectedSpeed: float = self.gameConfig.monsters[event.configId].speed
                    self.assertAlmostEqual(dist / time, expectedSpeed,
                        msg=f"MoveEvent has the wrong speed: {event}",
                        places=4)
                # Ensure spawned enemies don't overlap.
                if event.objType == ObjectType.MONSTER and event.startPos == spawnFp:
                    if lastSpawnedMoveEvent:
                        # Calculate previous enemy position at this time.
                        # This assumes the enemy leaves the spawn before they're killed.
                        amount = min(1.0, event.startTime / lastSpawnedMoveEvent.endTime)
                        curPos = lastSpawnedMoveEvent.startPos.interpolateTo(lastSpawnedMoveEvent.destPos, amount)
                        self.assertGreaterEqual(curPos.dist(spawnFp), 1.0)
                    lastSpawnedMoveEvent = event
            if event.eventType == EventType.DELETE:
                self.assertIn(event.id, activeIds)
                activeIds.discard(event.id)
                deleteById[event.id] = event
            if event.eventType == EventType.DAMAGE:
                damageById[event.id].append(event)
        # pytype: enable=attribute-error
        self.assertFalse(activeIds, msg=f"Not all IDs were deleted. Remaining: {activeIds}")

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

        enemiesSeen = 0
        for (id, events) in movesById.items():
            if events[0].objType == ObjectType.MONSTER:
                lastPos = spawnFp
            else:
                lastPos = None
            lastTime = None
            objType = events[0].objType
            configId = events[0].configId
            for event in events:
                # Ensure all moves are connected in space and time.
                if lastPos is not None:
                    self.assertEqual(lastPos, event.startPos)
                lastPos = event.destPos
                if lastTime:
                    self.assertEqual(lastTime, event.startTime)
                lastTime = event.endTime
                # Ensure object type and config ID are fixed for each object.
                self.assertEqual(objType, event.objType)
                self.assertEqual(configId, event.configId)
            if objType == ObjectType.MONSTER:
                # Ensure enemies are generated in the correct order.
                self.assertEqual(configId, wave[enemiesSeen])
                enemiesSeen += 1
                # Check if this enemy was defeated.
                self.assertIn(id, deleteById)
                deleteEvent = deleteById[id]
                if events[-1].destPos != exitFp or events[-1].endTime != deleteEvent.startTime:
                    # Enemy was defeated.
                    enemiesDefeated += 1
        self.assertEqual(enemiesSeen, len(wave))

        # Ensure damage always decreases enemy health.
        for (id, events) in damageById.items():
            configId = idToConfigId[id]
            health = self.gameConfig.monsters[configId].health
            errMsg = f"Enemy {id} (Config {configId}) starts with {health}. Events: {events}"
            for event in events:
                self.assertLess(event.health, health, msg=errMsg)
                health = event.health

        # Ensure battle time is positive.
        self.assertGreater(results.fb.TimeSecs(), 0.0)

        # Check monsters defeated data.
        monstersDefeated = MonstersDefeatedFb.MonstersDefeatedFbT.InitFromObj(results.fb.MonstersDefeated())
        totalMonstersSent = 0
        totalMonstersDefeated = 0
        seenConfigIds = set()
        for monsterDefeated in monstersDefeated.monstersDefeated:
            # Ensure we don't see duplicate config IDs
            self.assertNotIn(monsterDefeated.configId, seenConfigIds)
            seenConfigIds.add(monsterDefeated.configId)
            totalMonstersSent += monsterDefeated.numSent
            totalMonstersDefeated += monsterDefeated.numDefeated
        # Ensure all of the monsters sent add up to the wave size
        self.assertEqual(totalMonstersSent, len(wave))
        self.assertEqual(totalMonstersDefeated, enemiesDefeated)

class TestTowerFiringLongColumn(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # Use the real game config.
        gameConfigPath = Path('./game_config.json')
        with open(gameConfigPath) as gameConfigFile:
            gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
            # Change battlefield to one long column where we'll place towers on either side
            gameConfigData.playfield.numRows = 200
            gameConfigData.playfield.numCols = 3
            gameConfigData.playfield.monsterEnter = CellPos(0, 1)
            gameConfigData.playfield.monsterExit = CellPos(gameConfigData.playfield.numRows - 1, 1)
            self.gameConfig = GameConfig.fromGameConfigData(gameConfigData)
    
    @given(st.sampled_from([0, 2]), st.integers(20, 199), st.data())
    def test_towerFiresFirstShotCorrectly(self, towerCol: int, towerRow: int, data):
        # Pick a tower from any of the available ones.
        towerId = data.draw(st.sampled_from(sorted(self.gameConfig.towers.keys())))
        battleground = BattlegroundState.empty(self.gameConfig)
        battleground.towers.towers[towerRow][towerCol] = BgTowerState(TowerId(towerId))
        # Build the wave
        possibleMonsterIds = list(self.gameConfig.monsters.keys())
        monsterIndices = data.draw(st.lists(
            st.integers(0, len(possibleMonsterIds)-1),
            min_size=1))
        wave: List[ConfigId] = [possibleMonsterIds[i] for i in monsterIndices]

        battleComputer = BattleComputer(gameConfig = self.gameConfig)

        # First thing checked is that it doesn't throw an error.
        results = battleComputer.computeBattle(battleground, wave, useCpp=True)
        events = Battle.fbToEvents(results.fb.EventsNestedRoot())

        towerPos = FpCellPos(float(towerRow), float(towerCol))
        towerEvents = []
        damageEvents = []
        for event in events:
            if event.eventType == EventType.MOVE and event.objType == ObjectType.PROJECTILE:
                towerEvents.append(event)
                # Ensure every projectile is fired from the one tower.
                self.assertEqual(towerPos, event.startPos)
            if event.eventType == EventType.DAMAGE:
                damageEvents.append(event)

        # Ensure the tower has fired.
        self.assertGreater(len(towerEvents), 0, msg="The tower hasn't fired.")
        # Ensure the first shot fired is approximately at the range of the tower.
        towerConfig: TowerConfig = self.gameConfig.towers[towerId]
        firstEvent = towerEvents[0]
        dist = firstEvent.startPos.dist(firstEvent.destPos)
        self.assertAlmostEqual(dist, towerConfig.range, places=1)
        # Ensure every shot fired corresponds to damage dealt.
        self.assertEqual(len(towerEvents), len(damageEvents), msg="Shots fired don't match damage events.")

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
