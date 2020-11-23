from enum import Enum, unique, auto
import json
from typing import NewType, Any, Union, Dict, List
import math

import attr
import cattr

from infinitd_server.game_config import GameConfig, ConfigId, CellPos, MonsterConfig, ConfigId, BattleBonus, MonstersDefeated, BattleBonus, BonusCondition

FpRow = NewType('FpRow', float)
cattr.register_structure_hook(FpRow, lambda d, _: FpRow(d))
FpCol = NewType('FpCol', float)
cattr.register_structure_hook(FpCol, lambda d, _: FpCol(d))

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

    def distSq(self, other):
        return ((((self.row - other.row) * (self.row - other.row))) +
            ((self.col - other.col) * (self.col - other.col)))

    def dist(self, other):
        return math.sqrt(self.distSq(other))

    def interpolateTo(self, other, amount: float) -> Any:
        if amount < 0 or amount > 1:
            raise ValueError("amount must be between 0.0 and 1.0")

        return FpCellPos(
                FpRow(self.row * (1 - amount) + other.row * amount),
                FpCol(self.col * (1 - amount) + other.col * amount))

    def prettify(self, precision: int):
        return FpCellPos(FpRow(round(float(self.row), precision)), FpCol(round(float(self.col), precision)))

@unique
class ObjectType(Enum):
    MONSTER = auto()
    PROJECTILE = auto()

@unique
class EventType(Enum):
    MOVE = auto()
    DELETE = auto()
    DAMAGE = auto()

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

    def prettify(self, precision):
        return MoveEvent(
            objType = self.objType,
            id = self.id,
            configId = self.configId,
            startPos = self.startPos.prettify(precision),
            destPos = self.destPos.prettify(precision),
            startTime = round(self.startTime, precision),
            endTime = round(self.endTime, precision)
        )

@attr.s(frozen=True, auto_attribs=True)
class DeleteEvent:
    objType: ObjectType
    id: int
    startTime: float
    eventType: EventType = EventType.DELETE

    def prettify(self, precision):
        return DeleteEvent(
            objType = self.objType,
            id = self.id,
            startTime = round(self.startTime, precision),
        )

@attr.s(frozen=True, auto_attribs=True)
class DamageEvent:
    id: int
    startTime: float
    health: float
    eventType: EventType = EventType.DAMAGE

    def prettify(self, precision):
        return DamageEvent(
            id = self.id,
            startTime = round(self.startTime, precision),
            health = self.health,
        )

BattleEvent = Union[MoveEvent, DeleteEvent, DamageEvent]

def decodeEvent(eventObj: Dict, t) -> BattleEvent:
    if "eventType" not in eventObj:
        raise ValueError(f"Event object is missing event type: {eventObj}")
    if eventObj["eventType"] == EventType.MOVE.value:
        return cattr.structure(eventObj, MoveEvent)
    if eventObj["eventType"] == EventType.DELETE.value:
        return cattr.structure(eventObj, DeleteEvent)
    if eventObj["eventType"] == EventType.DAMAGE.value:
        return cattr.structure(eventObj, DamageEvent)
    raise ValueError(f"Unknown event type: {eventObj['eventType']}")

cattr.register_structure_hook(BattleEvent, decodeEvent)

@attr.s(frozen=True, auto_attribs=True)
class BattleResults:
    monstersDefeated: MonstersDefeated
    bonuses: List[ConfigId]
    reward: float
    timeSecs: float

    def allMonstersDefeated(self) -> bool:
        for (numSent, numDefeated) in self.monstersDefeated.values():
            if numSent != numDefeated:
                return False
        return True

    @property
    def goldPerMinute(self) -> float:
        minutes = max(1., self.timeSecs / 60.0)
        return round(self.reward / minutes, ndigits = 1)

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
    name: str
    events: List[BattleEvent]
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
