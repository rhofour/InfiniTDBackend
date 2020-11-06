from collections import deque
from dataclasses import dataclass, asdict
from random import Random
import math
from typing import List, Optional, Deque, Tuple, Sequence

from infinitdserver.battle import ObjectType, EventType, MoveEvent, DeleteEvent, DamageEvent, BattleResults, Battle, FpCellPos, BattleEvent, FpRow, FpCol
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.game_config import GameConfig, TowerConfig, CellPos, MonsterConfig, ProjectileConfig, ConfigId, MonstersDefeated
from infinitdserver.paths import PathMap, makePathMap, compressPath

EVENT_PRECISION = 4 # Number of decimal places to use for events

class BattleCalculationException(Exception):
    def __init__(self, battleground: BattlegroundState, message: str):
        self.battleground_json = battleground.to_json()
        self.message = message

@dataclass(frozen=False)
class TowerState:
    id: int
    config: TowerConfig
    pos: FpCellPos
    lastFired: float = -math.inf
    firingRadius: float = -1 # How far a projectile could have travelled at this point

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    path: List[CellPos]
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

    def __init__(self, gameConfig: GameConfig, seed: int = 42, gameTickSecs: float = 0.01):
        self.gameConfig = gameConfig
        self.startingSeed = seed
        self.gameTickSecs = gameTickSecs

    def getInitialTowerStates(self, battleground: BattlegroundState) -> List[TowerState]:
        nextId = 0
        towerStates = []
        for (row, towersCol) in enumerate(battleground.towers.towers):
            for (col, maybeTower) in enumerate(towersCol):
                if maybeTower is None:
                    continue
                towerStates.append(
                    TowerState(
                        id = nextId,
                        config = self.gameConfig.towers[maybeTower.id],
                        pos = FpCellPos(float(row), float(col)),
                    )
                )
                nextId += 1
        return towerStates

    def selectTarget(self, tower: TowerState, enemies: Sequence[MonsterState]) -> Optional[MonsterState]:
        farthestEnemy = None

        if tower.firingRadius <= 0:
            return None

        for enemy in enemies:
            if enemy.pos.dist(tower.pos) <= tower.firingRadius:
                if farthestEnemy is None or enemy.distTraveled > farthestEnemy.distTraveled:
                    farthestEnemy = enemy

        return farthestEnemy

    # Note: This code assumes enemies always move at a constant speed. It will
    # need to change to handle effects that may alter enemy speed (or
    # potentially stun them).
    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:
        events: List[BattleEvent] = []
        nextId = 0
        unspawnedMonsters = wave[::-1] # Reverse so we can pop off elements efficiently
        spawnedMonsters: Deque[MonsterState] = deque()
        gameTime = 0.0
        rand = Random(self.startingSeed)
        monstersDefeated: MonstersDefeated = {}
        towers = self.getInitialTowerStates(battleground)

        pathMap = makePathMap(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        if not pathMap:
            raise ValueError("Cannot compute battle with no path.")

        if not wave:
            raise ValueError("Cannot compute battle with empty wave.")

        spawnPoint = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        while unspawnedMonsters or spawnedMonsters:
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
                    raise BattleCalculationException(battleground,
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
                        raise BattleCalculationException(battleground,
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

                    endTime = newTime + timeToNewDest
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
                path = compressPath(pathMap.getRandomPath(self.gameConfig.playfield.numCols, rand))
                newMonster = MonsterState(
                        id = nextId,
                        config = monsterConfig,
                        pos = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter),
                        health = monsterConfig.health,
                        path = path)
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

            # Handle towers
            for tower in towers:
                # Check if a tower can fire again
                if tower.firingRadius == -1 and tower.config.firingRate > 0 and tower.lastFired + (1.0 / tower.config.firingRate) < gameTime:
                    tower.firingRadius = 0

                # Expand firing radius if it's not already at its maximum.
                if tower.firingRadius >= 0 and tower.firingRadius < tower.config.range:
                    tower.firingRadius = min(tower.config.range,
                            tower.firingRadius + (tower.config.projectileSpeed * self.gameTickSecs))

                # Fire at the farthest enemy within our firing radius.
                target = self.selectTarget(tower, spawnedMonsters)
                if target:
                    dist = target.pos.dist(tower.pos)
                    shotDuration = dist / tower.config.projectileSpeed

                    tower.lastFired = gameTime - shotDuration
                    if (tower.lastFired < 0):
                        raise BattleCalculationException(battleground,
                                f"Calculated tower firing time < 0: {tower.lastFired}\nDist: {dist} Duration: {shotDuration} Game time: {gameTime}")
                    tower.firingRadius = -1

                    target.health -= tower.config.damage

                    # Build and send the events
                    projectileMove = MoveEvent(
                        objType = ObjectType.PROJECTILE,
                        id = nextId,
                        configId = tower.config.projectileId,
                        startPos = tower.pos,
                        destPos = target.pos,
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
                        id = target.id,
                        startTime = gameTime,
                        health = target.health,
                    )
                    events.append(damageEvent)
                    if target.health <= 0:
                        deleteTargetEvent = DeleteEvent(
                            objType = ObjectType.MONSTER,
                            id = target.id,
                            startTime = gameTime,
                        )
                        events.append(deleteTargetEvent)
                        spawnedMonsters.remove(monster)
                    nextId += 1

            gameTime += self.gameTickSecs

        # Calculate bonuses using monstersDefeated
        battleResults = BattleResults.fromMonstersDefeated(
                monstersDefeated, self.gameConfig, gameTime)
        # Round the times in events
        events = [event.prettify(EVENT_PRECISION) for event in events]
        # Sort the events
        eventOrdering = {
            'MoveEvent': 0,
            'DamageEvent': 1,
            'DeleteEvent': 2,
        }
        return BattleCalcResults(
                events = sorted(events, key=lambda ev: (ev.startTime, eventOrdering[ev.__class__.__name__])),
                results = battleResults,
            )
