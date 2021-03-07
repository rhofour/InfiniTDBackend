import unittest
from collections import defaultdict
from dataclasses import dataclass, field
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

@dataclass
class ObjectData:
    configId: Optional[ConfigId]
    objType: Optional[ObjectType]
    moves: List[MoveEvent] = field(default_factory=list)
    damages: List[DamageEvent] = field(default_factory=list)
    delete: Optional[DeleteEvent] = None

class TestRandomBattlesRealConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # Use the real game config.
        gameConfigPath = Path('./game_config.json')
        with open(gameConfigPath) as gameConfigFile:
            gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
            self.gameConfig = GameConfig.fromGameConfigData(gameConfigData)

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
        battle = Battle(
            "random test battle", "test attacker", "test defender",
            events, results.results)
        # Something changes here, possibly because it's not a nested FB.
        reencodedEventsBytes = battle.encodeEventsFb()
        reencodedEventsFb = BattleEventsFb.BattleEventsFb.GetRootAsBattleEventsFb(reencodedEventsBytes, 0)
        remadeBattle = Battle(
            "re-encoded battle", "test attacker", "test defender",
            Battle.fbToEvents(reencodedEventsFb), results.results)
        tripleEncodedEventsBytes = remadeBattle.encodeEventsFb()
        # This should stay the same.
        self.assertEqual(reencodedEventsBytes, tripleEncodedEventsBytes)

        # Map every projectile fired to the tower it fired from.
        projFiredFrom: Dict[FpCellPos, List[MoveEvent]] = defaultdict(list)
        objDataById: Dict[int, ObjectData] = {}
        enemiesInOrder: List[int] = []
        # pytype: disable=attribute-error
        spawnFp = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        exitFp = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterExit)
        lastStartTime = 0.0
        # Ensure the first event is a move event starting at 0.0.
        firstEvent = events[0]
        self.assertEqual(firstEvent.eventType, EventType.MOVE)
        self.assertEqual(firstEvent.startTime, 0.0)
        for event in events:
            # Ensure events are in sorted order.
            self.assertGreaterEqual(event.startTime, lastStartTime, msg="Events are not sorted.")
            lastStartTime = event.startTime
            if event.eventType == EventType.MOVE:
                if event.objType == ObjectType.PROJECTILE:
                    projFiredFrom[event.startPos].append(event)
                if event.id not in objDataById:
                    objDataById[event.id] = ObjectData(configId=event.configId, objType=event.objType)
                    if event.objType == ObjectType.MONSTER:
                        enemiesInOrder.append(event.id)
                else:
                    # Ensure config ID and object type don't change for any objects.
                    self.assertEqual(event.configId, objDataById[event.id].configId)
                    self.assertEqual(event.objType, objDataById[event.id].objType)
                objDataById[event.id].configId = event.configId
                objDataById[event.id].objType = event.objType
                objDataById[event.id].moves.append(event)
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
            if event.eventType == EventType.DELETE:
                self.assertTrue(objDataById[event.id].moves, msg="Object is deleted before it exists.")
                self.assertIsNone(objDataById[event.id].delete, msg="Object was deleted more than once.")
                objDataById[event.id].delete = event
            if event.eventType == EventType.DAMAGE:
                objDataById[event.id].damages.append(event)
        # pytype: enable=attribute-error

        for (firedFrom, events) in projFiredFrom.items():
            # Ensure projectiles are fired from grid cells.
            self.assertEqual(firedFrom.row % 1, 0.0)
            self.assertEqual(firedFrom.col % 1, 0.0)
            # Look up tower associated with this position.
            tower = battleground.towers.towers[int(firedFrom.row)][int(firedFrom.col)]
            self.assertIsNotNone(tower)
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
                self.assertEqual(towerConfig.id, event.configId)
                # pytype: enable=attribute-error

        enemiesSeen = 0
        enemiesDefeated = 0
        for obj in objDataById.values():
            self.assertIsNotNone(obj.delete, msg="Object was never deleted.")

            # Ensure all move events are connected.
            if obj.objType == ObjectType.MONSTER:
                lastPos = spawnFp
            else:
                lastPos = None
            lastTime = None
            for move in obj.moves:
                # Ensure all moves are connected in space and time.
                if lastPos is not None:
                    self.assertEqual(lastPos, move.startPos)
                lastPos = move.destPos
                if lastTime:
                    self.assertEqual(lastTime, move.startTime)
                lastTime = move.endTime
            
            if obj.objType == ObjectType.MONSTER:
                # Ensure enemies are generated in the correct order.
                self.assertEqual(obj.configId, wave[enemiesSeen])
                # Keep track of the number of enemies spawned and defeated.
                enemiesSeen += 1
                # Check if this enemy was defeated.
                if obj.moves[-1].destPos != exitFp or obj.moves[-1].endTime != obj.delete.startTime:
                    enemiesDefeated += 1
                
                # Ensure damage always decreases enemy health.
                health = self.gameConfig.monsters[obj.configId].health
                errMsg = f"Enemy {id} (Config {obj.configId}) starts with {health}. Events: {obj.damages}"
                for event in obj.damages:
                    self.assertLess(event.health, health, msg=errMsg)
                    health = event.health

        self.assertEqual(enemiesSeen, len(wave))

        # Ensure spawned enemies don't overlap.
        lastEnemySpawned: Optional[ObjectData] = None
        for enemyId in enemiesInOrder:
            enemy = objDataById[enemyId]
            firstMove = enemy.moves[0]
            if lastEnemySpawned:
                # Do nothing if the last enemy died already.
                if lastEnemySpawned.delete.startTime > firstMove.startTime:
                    # Determine distance from spawn
                    lastEnemyMove = lastEnemySpawned.moves[0]
                    amount = min(1.0, firstMove.startTime / lastEnemyMove.endTime)
                    curPos = lastEnemyMove.startPos.interpolateTo(lastEnemyMove.destPos, amount)
                    self.assertGreaterEqual(curPos.dist(spawnFp), 1.0, msg="Enemies overlap with each other.")

            lastEnemySpawned = enemy

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
        results = battleComputer.computeBattle(battleground, wave)
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
            attackerName = "test attacker",
            defenderName = "test defender",
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
            attackerName = "test attacker",
            defenderName = "test defender",
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
