from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum, unique, auto
import math
from typing import List, Deque, NewType, Union, Dict, Any, Tuple, Optional
from random import Random
import json

import attr
import cattr

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.game_config import GameConfig, ConfigId, CellPos, MonsterConfig, ConfigId, BattleBonus, MonstersDefeated, BattleBonus, BonusCondition
from infinitdserver.paths import PathMap, makePathMap, compressPath

TIME_PRECISION = 4 # Number of decimal places to use for times

FpRow = NewType('FpRow', float)
cattr.register_structure_hook(FpRow, lambda d, _: FpRow(d))
FpCol = NewType('FpCol', float)
cattr.register_structure_hook(FpCol, lambda d, _: FpCol(d))

class BattleCalculationException(Exception):
    def __init__(self, battleground: BattlegroundState, message: str):
        self.battleground_json = battleground.to_json()
        self.message = message

@attr.s(frozen=True, auto_attribs=True)
class FpCellPos:
    row: FpRow
    col: FpCol

    @staticmethod
    def fromCellPos(cellPos: CellPos) -> Any:
        # TODO: fix this annotation when
        # https://github.com/Tinche/cattrs/issues/41 is fixed.
        return FpCellPos(FpRow(cellPos.row), FpCol(cellPos.col))

    def __eq__(self, other):
        return math.isclose(self.row, other.row) and math.isclose(self.col, other.col)

@unique
class ObjectType(Enum):
    MONSTER = auto()
    PROJECTILE = auto()

@unique
class EventType(Enum):
    MOVE = auto()
    DELETE = auto()

@attr.s(frozen=True, auto_attribs=True)
class MoveEvent:
    objType: ObjectType
    id: int # Uniquely refers to one monster or projectile
    configId: ConfigId # Which config to lookup
    startPos: FpCellPos
    destPos: FpCellPos
    startTime: float # When this movement starts
    endTime: float # When this movement ends
    eventType: EventType = EventType.MOVE

@attr.s(frozen=True, auto_attribs=True)
class DeleteEvent:
    objType: ObjectType
    id: int
    startTime: float
    eventType: EventType = EventType.DELETE

BattleEvent = Union[MoveEvent, DeleteEvent]

def decodeEvent(eventObj: Dict, t) -> BattleEvent:
    if "eventType" not in eventObj:
        raise ValueError(f"Event object is missing event type: {eventObj}")
    if eventObj["eventType"] == EventType.MOVE.value:
        return cattr.structure(eventObj, MoveEvent)
    if eventObj["eventType"] == EventType.DELETE.value:
        return cattr.structure(eventObj, DeleteEvent)
    raise ValueError(f"Unknown event type: {eventObj['eventType']}")

cattr.register_structure_hook(BattleEvent, decodeEvent)

@attr.s(frozen=True, auto_attribs=True)
class BattleResults:
    monstersDefeated: MonstersDefeated
    bonuses: List[ConfigId]
    reward: float
    timeSecs: float

    @staticmethod
    def fromMonstersDefeated(monstersDefeated: MonstersDefeated, gameConfig: GameConfig, timeSecs: float) -> Any:
        # First, calculate the base reward from monstersDefeated
        reward = 0.0
        for (monsterConfigId, (numDefeated, _)) in monstersDefeated.items():
            monsterConfig = gameConfig.monsters[monsterConfigId]
            reward += numDefeated * monsterConfig.bounty

        # Next, calculate which bonuses apply
        bonuses = []
        possibleBonuses = gameConfig.misc.battleBonuses
        for possibleBonusId in possibleBonuses:
            possibleBonus = gameConfig.misc.battleBonuses[possibleBonusId]
            if possibleBonus.isEarned(monstersDefeated):
                reward += possibleBonus.getAmount(reward)
                bonuses.append(possibleBonus.id)

        return BattleResults(
                monstersDefeated = monstersDefeated,
                bonuses = bonuses,
                reward = reward,
                timeSecs = timeSecs
            )

@attr.s(frozen=True, auto_attribs=True)
class Battle:
    events: List[BattleEvent]
    name: str
    results: BattleResults

    def encodeEvents(self) -> str:
        return json.dumps(cattr.unstructure(self.events))

    def encodeResults(self) -> str:
        return json.dumps(cattr.unstructure(self.results))

    @staticmethod
    def decodeEvents(encodedStr: str) -> Any:
        eventsList = json.loads(encodedStr)
        battleEvents = cattr.structure(eventsList, List[BattleEvent])
        return battleEvents

    @staticmethod
    def decodeResults(encodedStr: str) -> Any:
        resultsJson = json.loads(encodedStr)
        battleResults = cattr.structure(resultsJson, BattleResults)
        return battleResults

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    path: List[CellPos]
    targetInPath: int = 1

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
