from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum
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
    gameTickSecs: float = 0.01 # Period of the gameplay clock

    def __init__(self, gameConfig: GameConfig, seed: int = 42):
        self.gameConfig = gameConfig
        self.startingSeed = seed

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

        while unspawnedMonsters or spawnedMonsters:
            spawnOpen = True

            # Update existing monster positions

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
            break # TODO: Actually finish this

        return sorted(events, key=lambda ev: ev.startTime)
