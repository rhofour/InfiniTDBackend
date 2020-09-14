from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum
import math
from typing import List, Deque, NewType
import random

from dataclasses_json import dataclass_json

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.game_config import GameConfig, ConfigId, CellPos, MonsterConfig
from infinitdserver.paths import findShortestPaths, compressPath

FpRow = NewType('FpRow', float)
FpCol = NewType('FpCol', float)

@dataclass_json
@dataclass(frozen=True)
class FpCellPos:
    row: FpRow
    col: FpCol

    @staticmethod
    def fromCellPos(cellPos: CellPos) -> FpCellPos:
        return FpCellPos(FpRow(cellPos.row), FpCol(cellPos.col))

    def __eq__(self, other):
        return math.isclose(self.row, other.row) and math.isclose(self.col, other.col)

class EventType(Enum):
    MONSTER = 'monster'
    PROJECTILE = 'projectile'

@dataclass_json
@dataclass(frozen=True)
class BattleEvent:
    type: EventType
    id: int # Uniquely refers to one monster or projectile
    configId: ConfigId # Which config to lookup
    startPos: FpCellPos
    destPos: FpCellPos
    startTime: float # When this movement starts
    endTime: float # When this movement ends
    deleteAtEnd: bool # Whether this object should disappear on reaching its target
    # TODO: Add ability to reduce the health of a monster at the end

    def __eq__(self, other):
        return (self.type == other.type and
                self.id == other.id and
                self.configId == other.configId and
                self.startPos == other.startPos and
                self.destPos == other.destPos and
                math.isclose(self.startTime, other.startTime) and
                math.isclose(self.endTime, other.endTime) and
                self.deleteAtEnd == other.deleteAtEnd)

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    pathId: int
    targetInPath: int = 1

class BattleComputer:
    startingSeed: int
    gameConfig: GameConfig
    gameTickSecs: float # Period of the gameplay clock

    def __init__(self, gameConfig: GameConfig, seed: int = 42, gameTickSecs: float = 0.01):
        self.gameConfig = gameConfig
        self.startingSeed = seed
        self.gameTickSecs = gameTickSecs

    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> List[BattleEvent]:
        events: List[BattleEvent] = []
        nextMonsterId = 0
        nextProjectileId = 0
        unspawnedMonsters = wave[::-1] # Reverse so we can pop off elements efficiently
        spawnedMonsters: Deque[MonsterState] = deque()
        gameTime = 0.0
        random.seed(self.startingSeed)

        paths = findShortestPaths(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        paths = [compressPath(path) for path in paths]
        if not paths:
            raise ValueError("Cannot compute battle with no path.")

        spawnPoint = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter)
        while unspawnedMonsters or spawnedMonsters:
            spawnOpen = True

            # Update existing monster positions
            finishedMonsters = []
            for monster in spawnedMonsters:
                path = paths[monster.pathId]
                dest = path[monster.targetInPath]
                distPerTick = monster.config.speed * self.gameTickSecs

                if monster.pos.row == float(dest.row):
                    initialDist = abs(monster.pos.col - dest.col)
                    movingHorizontally = True
                elif monster.pos.col == float(dest.col): # Moving vertically
                    initialDist = abs(monster.pos.row - dest.row)
                    movingHorizontally = False
                else:
                    raise Exception(f"Monster isn't lined up with destination. Monster {monster.pos} Dest {dest}")

                remainingDist = distPerTick - initialDist
                if remainingDist < 0: # Advance normally
                    if movingHorizontally:
                        if float(dest.col) > monster.pos.col:
                            monster.pos = FpCellPos(monster.pos.row, monster.pos.col + distPerTick)
                        else:
                            monster.pos = FpCellPos(monster.pos.row, monster.pos.col - distPerTick)
                    else:
                        if float(dest.row) > monster.pos.row:
                            monster.pos = FpCellPos(monster.pos.row + distPerTick, monster.pos.col)
                        else:
                            monster.pos = FpCellPos(monster.pos.row - distPerTick, monster.pos.col)
                else: # Either finish the path or move to the next segment
                    if monster.targetInPath == len(path) - 1: # We reached the end
                        finishedMonsters.append(monster)
                        continue
                    # Continue to the next segment of the path
                    monster.targetInPath += 1
                    newDest = path[monster.targetInPath]
                    if movingHorizontally: # Now we're moving vertically
                        if newDest.row > dest.col:
                            monster.pos = FpCellPos(FpRow(dest.row + remainingDist), FpCol(dest.col))
                        else:
                            monster.pos = FpCellPos(FpRow(dest.row - remainingDist), FpCol(dest.col))
                        timeToNewDest = abs(newDest.row - monster.pos.row) / monster.config.speed
                    else: # Now we'removing horizontally
                        if newDest.col > dest.col:
                            monster.pos = FpCellPos(FpRow(dest.row), FpCol(dest.col + remainingDist))
                        else:
                            monster.pos = FpCellPos(FpRow(dest.row), FpCol(dest.col - remainingDist))
                        timeToNewDest = abs(newDest.col - monster.pos.col) / monster.config.speed
                    newEvent = BattleEvent(
                        type = EventType.MONSTER,
                        id = monster.id,
                        configId = monster.config.id,
                        startPos = FpCellPos.fromCellPos(dest),
                        destPos = FpCellPos.fromCellPos(newDest),
                        startTime = gameTime + initialDist / monster.config.speed,
                        endTime = gameTime + timeToNewDest,
                        deleteAtEnd = monster.targetInPath == len(path) - 1,
                    )
                    events.append(newEvent)

                if abs(spawnPoint.row - monster.pos.row) < 1 and abs(spawnPoint.col - monster.pos.col) < 1:
                    spawnOpen = False

            for monster in finishedMonsters:
                spawnedMonsters.remove(monster)

            if spawnOpen and unspawnedMonsters:
                monsterConfigId = unspawnedMonsters.pop()
                try:
                    monsterConfig = self.gameConfig.monsters[monsterConfigId]
                except KeyError:
                    raise ValueError(f"Unknown monster ID: {monsterConfigId}")
                pathId = random.randrange(0, len(paths))
                path = paths[pathId]
                newMonster = MonsterState(
                        id = nextMonsterId,
                        config = monsterConfig,
                        pos = FpCellPos.fromCellPos(self.gameConfig.playfield.monsterEnter),
                        health = monsterConfig.health,
                        pathId = pathId)
                nextMonsterId += 1
                spawnedMonsters.append(newMonster)
                startPos: FpCellPos = FpCellPos.fromCellPos(path[0])
                destPos: FpCellPos = FpCellPos.fromCellPos(path[1])
                dist = max(abs(startPos.row - destPos.row), abs(startPos.col - destPos.col))
                newMonsterEvent = BattleEvent(
                    type = EventType.MONSTER,
                    id = newMonster.id,
                    configId = newMonster.config.id,
                    startPos = startPos,
                    destPos = destPos,
                    startTime = gameTime,
                    endTime = gameTime + (dist / monsterConfig.speed),
                    deleteAtEnd = len(path) == 2,
                )
                events.append(newMonsterEvent)

            gameTime += self.gameTickSecs

        return sorted(events, key=lambda ev: ev.startTime)
