from dataclasses import dataclass, asdict
from random import Random
import math
from typing import List, Optional, Tuple, Sequence
import json

import cattr

from infinitd_server.battle import ObjectType, EventType, MoveEvent, DeleteEvent, DamageEvent, BattleResults, Battle, FpCellPos, BattleEvent, FpRow, FpCol
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.game_config import GameConfig, TowerConfig, CellPos, MonsterConfig, ProjectileConfig, ConfigId, MonstersDefeated
from infinitd_server.paths import PathMap, makePathMap, compressPath
from infinitd_server.cpp_battle_computer.battle_computer import BattleComputer as CppBattleComputer

EVENT_PRECISION = 4 # Number of decimal places to use for events

class BattleCalculationException(Exception):
    def __init__(self, battleground: BattlegroundState, wave: List[ConfigId], message: str):
        self.battleground_json = battleground.to_json()
        self.message = message

@dataclass(frozen=False)
class TowerState:
    id: int
    config: TowerConfig
    pos: FpCellPos
    lastFired: float
    firingRadius: float = -1 # How far a projectile could have travelled at this point
    firingRadiusSq: float = -1

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    path: List[CellPos]
    spawnedAt: float
    targetInPath: int = 1
    distTraveled: float = 0.0

@dataclass(frozen=True)
class BattleCalcResults:
    events: List[BattleEvent]
    results: BattleResults


class BattleComputer:
    startingSeed: int
    gameConfig: GameConfig
    gameTickSecs: float # Period of the gameplay clock
    debug: bool
    cppBattleComputer: CppBattleComputer

    def __init__(self, gameConfig: GameConfig, seed: int = 42, gameTickSecs: float = 0.01, debug = False):
        self.gameConfig = gameConfig
        self.startingSeed = seed
        self.gameTickSecs = gameTickSecs
        self.debug = debug
        jsonText = json.dumps(cattr.unstructure(gameConfig.gameConfigData))
        self.cppBattleComputer = CppBattleComputer(gameConfig, jsonText)
        print(f"Made BattleComputer with seed {self.startingSeed}")

    def getInitialTowerStates(self, battleground: BattlegroundState) -> List[TowerState]:
        nextId = 0
        towerStates = []
        for (row, towersCol) in enumerate(battleground.towers.towers):
            for (col, maybeTower) in enumerate(towersCol):
                if maybeTower is None:
                    continue
                config = self.gameConfig.towers[maybeTower.id]
                towerStates.append(
                    TowerState(
                        id = nextId,
                        config = config,
                        pos = FpCellPos(FpRow(row), FpCol(col)),
                        lastFired = -(1 / config.firingRate) if config.firingRate > 0 else -1,
                    )
                )
                nextId += 1
        return towerStates

    @staticmethod
    def selectTarget(tower: TowerState, enemies: Sequence[MonsterState], gameTime: float
            ) -> Optional[Tuple[MonsterState, float]]:

        if tower.firingRadius <= 0:
            return None

        for enemy in enemies:
            distSq = enemy.pos.distSq(tower.pos)
            if distSq <= tower.firingRadiusSq:
                dist = math.sqrt(distSq)
                timeToHit = dist / tower.config.projectileSpeed
                if gameTime - timeToHit < enemy.spawnedAt:
                    continue # Don't allow targetting enemies before they've spawned.
                # Assumes enemies are sorted by decreasing distTraveled so we
                # can return the first one we can hit.
                return (enemy, dist)

        return None

    # Note: This code assumes enemies always move at a constant speed. It will
    # need to change to handle effects that may alter enemy speed (or
    # potentially stun them).
    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:

        events: List[BattleEvent] = []
        nextId = 0
        unspawnedMonsters = wave[::-1] # Reverse so we can pop off elements efficiently
        spawnedMonsters: List[MonsterState] = []
        gameTime = 0.0
        ticks = 0
        rand = Random(self.startingSeed)
        monstersDefeated: MonstersDefeated = {}
        towers = self.getInitialTowerStates(battleground)

        if not wave:
            raise ValueError("Cannot compute battle with empty wave.")

        pathMap = makePathMap(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        if not pathMap:
            raise ValueError("Cannot compute battle with no path.")

        # Calculate paths for all enemies ahead of time.
        paths = []
        longestPath = 0
        for _ in wave:
            paths.append(compressPath(pathMap.getRandomPath(
                self.gameConfig.playfield.monsterEnter, rand)))

        self.cppBattleComputer.computeBattle(battleground, wave, paths)

        # Reverse so we can use these efficiently in Python. Remove when
        # everything works in C++.
        paths.reverse()

        spawnPoint = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        while unspawnedMonsters or spawnedMonsters:
            gameTime = ticks * self.gameTickSecs
            # Update existing monster positions
            spawnOpen = True
            finishedMonsters = []
            for monster in spawnedMonsters:
                dest = monster.path[monster.targetInPath]
                distPerTick = monster.config.speed * self.gameTickSecs

                if monster.pos.row == float(dest.row):
                    initialDist = abs(monster.pos.col - dest.col)
                    movingHorizontally = True
                elif monster.pos.col == float(dest.col): # Moving vertically
                    initialDist = abs(monster.pos.row - dest.row)
                    movingHorizontally = False
                else:
                    raise BattleCalculationException(battleground, wave,
                            f"Monster {monster.id} isn't lined up with destination. Monster {monster.pos} Dest {dest}")

                # Remaining dist is how far the enemy can move after reaching
                # the destination.
                remainingDist = distPerTick - initialDist
                if remainingDist < 0: # Advance normally
                    if movingHorizontally:
                        if float(dest.col) > monster.pos.col:
                            monster.pos = FpCellPos(
                                    FpRow(monster.pos.row), FpCol(monster.pos.col + distPerTick))
                        else:
                            monster.pos = FpCellPos(
                                    FpRow(monster.pos.row), FpCol(monster.pos.col - distPerTick))
                    else:
                        if float(dest.row) > monster.pos.row:
                            monster.pos = FpCellPos(
                                    FpRow(monster.pos.row + distPerTick), FpCol(monster.pos.col))
                        else:
                            monster.pos = FpCellPos(
                                    FpRow(monster.pos.row - distPerTick), FpCol(monster.pos.col))
                else: # Either finish the path or move to the next segment
                    # Time between ticks where we start the next path / reach
                    # the end. This is always <= gameTime because gameTime is
                    # the time at which the monsters have finished moving.
                    newTime = gameTime - self.gameTickSecs + (initialDist / monster.config.speed)
                    if monster.targetInPath == len(monster.path) - 1: # We reached the end
                        deleteEvent = DeleteEvent(
                            objType = ObjectType.MONSTER,
                            id = monster.id,
                            startTime = newTime,
                        )
                        events.append(deleteEvent)
                        finishedMonsters.append(monster)
                        continue

                    # Continue to the next segment of the path
                    monster.targetInPath += 1
                    newDest = monster.path[monster.targetInPath]
                    # Figure out if we're moving horizontally for vertically
                    if dest.row == float(newDest.row):
                        movingHorizontally = True
                    elif dest.col == float(newDest.col): # Moving vertically
                        movingHorizontally = False
                    else:
                        raise BattleCalculationException(battleground, wave,
                                f"Monster {monster.id} isn't lined up with new destination. Monster {monster.pos} NewDest {dest}")
                    if movingHorizontally:
                        if newDest.col > dest.col:
                            monster.pos = FpCellPos(FpRow(dest.row), FpCol(dest.col + remainingDist))
                        else:
                            monster.pos = FpCellPos(FpRow(dest.row), FpCol(dest.col - remainingDist))
                        timeToNewDest = abs(newDest.col - monster.pos.col) / monster.config.speed
                    else:
                        if newDest.row > dest.col:
                            monster.pos = FpCellPos(FpRow(dest.row + remainingDist), FpCol(dest.col))
                        else:
                            monster.pos = FpCellPos(FpRow(dest.row - remainingDist), FpCol(dest.col))
                        timeToNewDest = abs(newDest.row - monster.pos.row) / monster.config.speed

                    endTime = gameTime + timeToNewDest
                    newEvent = MoveEvent(
                        objType = ObjectType.MONSTER,
                        id = monster.id,
                        configId = monster.config.id,
                        startPos = FpCellPos.fromCellPos(dest),
                        destPos = FpCellPos.fromCellPos(newDest),
                        startTime = newTime,
                        endTime = endTime,
                    )
                    events.append(newEvent)

                monster.distTraveled += distPerTick
                if abs(spawnPoint.row - monster.pos.row) < 1 and abs(spawnPoint.col - monster.pos.col) < 1:
                    spawnOpen = False

            # If possible, spawn the next monster
            if spawnOpen and unspawnedMonsters:
                monsterConfigId = unspawnedMonsters.pop()
                try:
                    monsterConfig = self.gameConfig.monsters[monsterConfigId]
                except KeyError:
                    raise ValueError(f"Unknown monster ID: {monsterConfigId}")
                path = paths.pop()
                newMonster = MonsterState(
                        id = nextId,
                        config = monsterConfig,
                        pos = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter),
                        health = monsterConfig.health,
                        path = path,
                        spawnedAt = gameTime)
                nextId += 1
                spawnedMonsters.append(newMonster)

                # Update monsters defeated dict to note the new monster
                prevMonstersDefeatedState = monstersDefeated.get(monsterConfig.id, (0, 0))
                monstersDefeated[monsterConfig.id] = (
                        prevMonstersDefeatedState[0], prevMonstersDefeatedState[1] + 1)

                # Add the battle events for the new monster
                startPos: FpCellPos = FpCellPos.fromCellPos(path[0])
                destPos: FpCellPos = FpCellPos.fromCellPos(path[1])
                dist = max(abs(startPos.row - destPos.row), abs(startPos.col - destPos.col))
                endTime = gameTime + (dist / monsterConfig.speed)
                newMonsterEvent = MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = newMonster.id,
                    configId = newMonster.config.id,
                    startPos = startPos,
                    destPos = destPos,
                    startTime = gameTime,
                    endTime = endTime,
                )
                events.append(newMonsterEvent)

            for monster in finishedMonsters:
                spawnedMonsters.remove(monster)

            # Sort monsters by distance traveled to make target selection
            # easier.
            spawnedMonsters = sorted(spawnedMonsters, key=lambda x: x.distTraveled, reverse=True)

            # Handle towers
            for tower in towers:
                # Update firing radius
                if tower.config.firingRate > 0:
                    timeSinceAbleToFire = gameTime - (tower.lastFired + (1.0 / tower.config.firingRate))
                    tower.firingRadius = max(0, min(tower.config.range, timeSinceAbleToFire * tower.config.projectileSpeed))
                    tower.firingRadiusSq = tower.firingRadius * tower.firingRadius

                # Fire at the farthest enemy within our firing radius.
                target = BattleComputer.selectTarget(tower, spawnedMonsters, gameTime)
                if target:
                    targetEnemy, targetDist = target
                    shotDuration = targetDist / tower.config.projectileSpeed

                    # Round here so tiny FP errors don't lead to a battle calculation exception.
                    tower.lastFired = round(gameTime - shotDuration, EVENT_PRECISION)
                    if (tower.lastFired < 0):
                        raise BattleCalculationException(battleground, wave,
                                f"Calculated tower firing time < 0: {tower.lastFired}\nDist: {dist} Duration: {shotDuration} Game time: {gameTime}")

                    targetEnemy.health -= tower.config.damage

                    # Build and send the events
                    projectileMove = MoveEvent(
                        objType = ObjectType.PROJECTILE,
                        id = nextId,
                        configId = tower.config.projectileId,
                        startPos = tower.pos,
                        destPos = targetEnemy.pos,
                        startTime = tower.lastFired,
                        endTime = gameTime,
                    )
                    events.append(projectileMove)
                    projectileDelete = DeleteEvent(
                        objType = ObjectType.PROJECTILE,
                        id = nextId,
                        startTime = gameTime,
                    )
                    events.append(projectileDelete)
                    damageEvent = DamageEvent(
                        id = targetEnemy.id,
                        startTime = gameTime,
                        health = targetEnemy.health,
                    )
                    events.append(damageEvent)
                    if targetEnemy.health <= 0:
                        prevMonstersDefeatedState = monstersDefeated[targetEnemy.config.id]
                        monstersDefeated[targetEnemy.config.id] = (prevMonstersDefeatedState[0] + 1, prevMonstersDefeatedState[1])
                        deleteTargetEvent = DeleteEvent(
                            objType = ObjectType.MONSTER,
                            id = targetEnemy.id,
                            startTime = gameTime,
                        )
                        events.append(deleteTargetEvent)
                        spawnedMonsters.remove(targetEnemy)
                    nextId += 1

            ticks += 1

        # Calculate bonuses using monstersDefeated
        battleResults = BattleResults.fromMonstersDefeated(
                monstersDefeated, self.gameConfig, round(gameTime, EVENT_PRECISION))
        # Round the times in events
        events = [event.prettify(EVENT_PRECISION) for event in events]
        # Sort the events
        eventOrdering = {
            'MoveEvent': 0,
            'DamageEvent': 1,
            'DeleteEvent': 2,
        }
        def eventToSortKeys(event: BattleEvent):
            try:
                return (event.startTime, eventOrdering[event.__class__.__name__], event.endTime) # pytype: disable=attribute-error
            except AttributeError:
                return (event.startTime, eventOrdering[event.__class__.__name__], -1)
        sortedEvents = sorted(events, key=eventToSortKeys)

        if self.debug:
            deletedIds = set()
            deletedEventIndex = {}

            for (i, event) in enumerate(sortedEvents):
                if event.eventType == EventType.DELETE:
                    if event.id in deletedIds:
                        raise BattleCalculationException(battleground, wave,
                            f"Duplicate event to delete {event.id}, previous event at index {deletedEventIndex[event.id]}: {event}")
                    deletedIds.add(event.id)
                    deletedEventIndex[event.id] = i
                else:
                    if event.id in deletedIds:
                        raise BattleCalculationException(battleground, wave,
                            f"Received an event with ID {event.id}, but {event.id} was deleted earlier in event at index "
                            "{deletedEventIndex[event.id]}: {event}")

        return BattleCalcResults(
                events = sortedEvents,
                results = battleResults,
            )
