from collections import deque
from dataclasses import dataclass, asdict
from random import Random
import math
from typing import List, Optional, Deque, Tuple

from infinitdserver.battle import ObjectType, EventType, MoveEvent, DeleteEvent, BattleResults, Battle, FpCellPos, BattleEvent, FpRow, FpCol
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.game_config import GameConfig, TowerConfig, CellPos, MonsterConfig, ProjectileConfig, ConfigId, MonstersDefeated
from infinitdserver.paths import PathMap, makePathMap, compressPath

TIME_PRECISION = 4 # Number of decimal places to use for times

class BattleCalculationException(Exception):
    def __init__(self, battleground: BattlegroundState, message: str):
        self.battleground_json = battleground.to_json()
        self.message = message

@dataclass(frozen=False)
class TowerState:
    id: int
    config: TowerConfig
    pos: CellPos
    lastFired: float

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    path: List[CellPos]
    targetInPath: int = 1

    def timeLeft(self) -> float:
        """timeLeft returns how many seconds until this enemy reaches their destination."""
        curTargetIdx = self.targetInPath
        curTarget = FpCellPos.fromCellPos(self.path[curTargetIdx])
        timeLeft = self.pos.dist(curTarget) / self.config.speed
        curTargetIdx += 1

        while curTargetIdx < len(self.path):
            nextTarget = FpCellPos.fromCellPos(self.path[curTargetIdx])
            timeLeft += curTarget.dist(nextTarget) / self.config.speed
            curTarget = nextTarget
            curTargetIdx += 1

        return timeLeft

    def posInFuture(self, timeDelta: float) -> Optional[FpCellPos]:
        if timeDelta < 0:
            raise ValueError("Future times not supported.")

        curPos = self.pos
        curTargetIdx = self.targetInPath
        curTarget = self.path[curTargetIdx]
        timeToTarget = curPos.dist(curTarget) / self.config.speed

        while timeDelta > timeToTarget:
            # Move forward
            timeDelta -= timeToTarget
            curPos = FpCellPos.fromCellPos(curTarget)
            if curTargetIdx + 1 == len(self.path):
                return None # Enemy will reach the end
            curTargetIdx += 1
            curTarget = self.path[curTargetIdx]
            timeToTarget = curPos.dist(curTarget) / self.config.speed

        return curPos.interpolateTo(curTarget, timeDelta / timeToTarget)

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

    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:
        events: List[BattleEvent] = []
        nextId = 0
        unspawnedMonsters = wave[::-1] # Reverse so we can pop off elements efficiently
        spawnedMonsters: Deque[MonsterState] = deque()
        gameTime = 0.0
        rand = Random(self.startingSeed)
        monstersDefeated: MonstersDefeated = {}

        pathMap = makePathMap(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        if not pathMap:
            raise ValueError("Cannot compute battle with no path.")

        if not wave:
            raise ValueError("Cannot compute battle with empty wave.")

        spawnPoint = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        spawnOpen = True
        while unspawnedMonsters or spawnedMonsters:
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
                endTime = round(gameTime + (dist / monsterConfig.speed), TIME_PRECISION)
                newMonsterEvent = MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = newMonster.id,
                    configId = newMonster.config.id,
                    startPos = startPos,
                    destPos = destPos,
                    startTime = round(gameTime, TIME_PRECISION),
                    endTime = endTime,
                )
                events.append(newMonsterEvent)
                if (len(path) == 2):
                    deleteEvent = DeleteEvent(
                        objType = ObjectType.MONSTER,
                        id = newMonster.id,
                        startTime = endTime,
                    )
                    events.append(deleteEvent)

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
                    if monster.targetInPath == len(monster.path) - 1: # We reached the end
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

                    endTime = round(gameTime + self.gameTickSecs + timeToNewDest, TIME_PRECISION)
                    newEvent = MoveEvent(
                        objType = ObjectType.MONSTER,
                        id = monster.id,
                        configId = monster.config.id,
                        startPos = FpCellPos.fromCellPos(dest),
                        destPos = FpCellPos.fromCellPos(newDest),
                        startTime = round(gameTime + initialDist / monster.config.speed, TIME_PRECISION),
                        endTime = endTime,
                    )
                    events.append(newEvent)
                    if monster.targetInPath == len(monster.path) - 1:
                        deleteEvent = DeleteEvent(
                            objType = ObjectType.MONSTER,
                            id = monster.id,
                            startTime = endTime,
                        )
                        events.append(deleteEvent)

                if abs(spawnPoint.row - monster.pos.row) < 1 and abs(spawnPoint.col - monster.pos.col) < 1:
                    spawnOpen = False

            for monster in finishedMonsters:
                spawnedMonsters.remove(monster)

            gameTime += self.gameTickSecs

        # Calculate bonuses using monstersDefeated
        battleResults = BattleResults.fromMonstersDefeated(
                monstersDefeated, self.gameConfig, gameTime)
        return BattleCalcResults(
                events = sorted(events, key=lambda ev: ev.startTime),
                results = battleResults,
            )
