from dataclasses import dataclass
from enum import Enum, unique, auto
import json
from typing import NewType, Any, Union, Dict, List
import math

import attr
import cattr
import flatbuffers

from infinitd_server.game_config import GameConfig, ConfigId, CellPos, MonsterConfig, ConfigId, BattleBonus, MonstersDefeated, BattleBonus, BonusCondition
import  InfiniTDFb.FpCellPosFb as FpCellPosFb
import  InfiniTDFb.ObjectTypeFb as ObjectTypeFb
import  InfiniTDFb.MoveEventFb as MoveEventFb
import  InfiniTDFb.DeleteEventFb as DeleteEventFb
import  InfiniTDFb.DamageEventFb as DamageEventFb
import  InfiniTDFb.BattleEventFb as BattleEventFb
import  InfiniTDFb.BattleEventUnionFb as BattleEventUnionFb
import  InfiniTDFb.MonsterDefeatedFb as MonsterDefeatedFb
import  InfiniTDFb.MonstersDefeatedFb as MonstersDefeatedFb
import  InfiniTDFb.BattleResultsFb as BattleResultsFb
import  InfiniTDFb.BattleEventsFb as BattleEventsFb
import  InfiniTDFb.BattleCalcResultsFb as BattleCalcResultsFb

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

    def toFb(self, builder):
        return FpCellPosFb.CreateFpCellPosFb(builder, self.row, self.col)

    @staticmethod
    def fromFb(fb):
        return FpCellPos(fb.Row(), fb.Col())

@unique
class ObjectType(Enum):
    MONSTER = auto()
    PROJECTILE = auto()

    @classmethod
    def toFb(cls, x):
        if x == cls.MONSTER:
            return ObjectTypeFb.ObjectTypeFb().ENEMY
        elif x == cls.PROJECTILE:
            return ObjectTypeFb.ObjectTypeFb().PROJECTILE
        raise ValueError(f"Unknown enum value: {x}")

    @classmethod
    def fromFb(cls, x):
        if x == ObjectTypeFb.ObjectTypeFb().ENEMY:
            return cls.MONSTER
        elif x == ObjectTypeFb.ObjectTypeFb().PROJECTILE:
            return cls.PROJECTILE
        raise ValueError(f"Unknown enum value: {x}")

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

    def toFb(self, builder):
        MoveEventFb.MoveEventFbStart(builder)
        MoveEventFb.MoveEventFbAddObjType(builder, ObjectType.toFb(self.objType))
        MoveEventFb.MoveEventFbAddId(builder, self.id)
        MoveEventFb.MoveEventFbAddConfigId(builder, self.configId)
        MoveEventFb.MoveEventFbAddStartPos(builder, self.startPos.toFb(builder))
        MoveEventFb.MoveEventFbAddDestPos(builder, self.destPos.toFb(builder))
        MoveEventFb.MoveEventFbAddStartTime(builder, self.startTime)
        MoveEventFb.MoveEventFbAddEndTime(builder, self.endTime)
        event = MoveEventFb.MoveEventFbEnd(builder)

        BattleEventFb.BattleEventFbStart(builder)
        BattleEventFb.BattleEventFbAddEventType(builder,
                BattleEventUnionFb.BattleEventUnionFb().Move)
        BattleEventFb.BattleEventFbAddEvent(builder, event)
        return BattleEventFb.BattleEventFbEnd(builder)

    @staticmethod
    def fromFb(fb):
        return MoveEvent(ObjectType.fromFb(fb.ObjType()),
                fb.Id(),
                fb.ConfigId(),
                FpCellPos.fromFb(fb.StartPos()),
                FpCellPos.fromFb(fb.DestPos()),
                fb.StartTime(),
                fb.EndTime())

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

    def toFb(self, builder):
        DeleteEventFb.DeleteEventFbStart(builder)
        DeleteEventFb.DeleteEventFbAddObjType(builder, ObjectType.toFb(self.objType))
        DeleteEventFb.DeleteEventFbAddId(builder, self.id)
        DeleteEventFb.DeleteEventFbAddStartTime(builder, self.startTime)
        event = DeleteEventFb.DeleteEventFbEnd(builder)

        BattleEventFb.BattleEventFbStart(builder)
        BattleEventFb.BattleEventFbAddEventType(builder,
                BattleEventUnionFb.BattleEventUnionFb().Delete)
        BattleEventFb.BattleEventFbAddEvent(builder, event)
        return BattleEventFb.BattleEventFbEnd(builder)

    @staticmethod
    def fromFb(fb):
        return DeleteEvent(ObjectType.fromFb(fb.ObjType()),
                fb.Id(),
                fb.StartTime())

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

    def toFb(self, builder):
        DamageEventFb.DamageEventFbStart(builder)
        DamageEventFb.DamageEventFbAddId(builder, self.id)
        DamageEventFb.DamageEventFbAddStartTime(builder, self.startTime)
        DamageEventFb.DamageEventFbAddHealth(builder, self.health)
        event = DamageEventFb.DamageEventFbEnd(builder)

        BattleEventFb.BattleEventFbStart(builder)
        BattleEventFb.BattleEventFbAddEventType(builder,
                BattleEventUnionFb.BattleEventUnionFb().Damage)
        BattleEventFb.BattleEventFbAddEvent(builder, event)
        return BattleEventFb.BattleEventFbEnd(builder)

    @staticmethod
    def fromFb(fb):
        return DamageEvent(fb.Id(),
                fb.StartTime(),
                fb.Health())

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
    def decodeMonstersDefeated(monstersDefeatedFb: MonstersDefeatedFb) -> MonstersDefeated:
        numMonstersDefeated = monstersDefeatedFb.MonstersDefeatedLength()
        monstersDefeated = {}
        for i in range(numMonstersDefeated):
            monsterDefeatedFb = monstersDefeatedFb.MonstersDefeated(i)
            monstersDefeated[monsterDefeatedFb.ConfigId()] = (
                    monsterDefeatedFb.NumDefeated(), monsterDefeatedFb.NumSent())
        return monstersDefeated

    @staticmethod
    def encodeMonstersDefeated(builder, monstersDefeated: MonstersDefeated):
        MonstersDefeatedFb.MonstersDefeatedFbStartMonstersDefeatedVector(
                builder, len(monstersDefeated))
        for (configId, (numDefeated, numSent)) in reversed(monstersDefeated.items()):
            MonsterDefeatedFb.CreateMonsterDefeatedFb(builder,
                configId = configId,
                numDefeated = numDefeated,
                numSent = numSent)
        monstersDefeatedVector = builder.EndVector()
        MonstersDefeatedFb.MonstersDefeatedFbStart(builder)
        MonstersDefeatedFb.MonstersDefeatedFbAddMonstersDefeated(builder, monstersDefeatedVector)
        return MonstersDefeatedFb.MonstersDefeatedFbEnd(builder)

    @staticmethod
    def fromMonstersDefeatedFb(monstersDefeatedFb: MonstersDefeatedFb, gameConfig: GameConfig, timeSecs: float) -> Any:
        return BattleResults.fromMonstersDefeated(
                BattleResults.decodeMonstersDefeated(monstersDefeatedFb),
                gameConfig, timeSecs)

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

    def encodeFb(self) -> bytearray:
        builder = flatbuffers.Builder(256)
        monstersDefeated = BattleResults.encodeMonstersDefeated(builder, self.monstersDefeated)

        BattleResultsFb.BattleResultsFbStartBonusesVector(builder, len(self.bonuses))
        for bonus in reversed(self.bonuses):
            builder.PrependUint16(bonus)
        bonusesVector = builder.EndVector()

        BattleResultsFb.BattleResultsFbStart(builder)
        BattleResultsFb.BattleResultsFbAddMonstersDefeated(builder, monstersDefeated)
        BattleResultsFb.BattleResultsFbAddBonuses(builder, bonusesVector)
        BattleResultsFb.BattleResultsFbAddReward(builder, self.reward)
        BattleResultsFb.BattleResultsFbAddTimeSecs(builder, self.timeSecs)
        battleResults = BattleResultsFb.BattleResultsFbEnd(builder)
        builder.Finish(battleResults)
        return builder.Output()

    @staticmethod
    def decodeFb(encodedBytes: bytearray):
        resultsFb = BattleResultsFb.BattleResultsFb.GetRootAsBattleResultsFb(encodedBytes, 0)

        monstersDefeatedFb = resultsFb.MonstersDefeated()
        monstersDefeated = BattleResults.decodeMonstersDefeated(monstersDefeatedFb)

        numBonuses = resultsFb.BonusesLength()
        bonuses = []
        for i in range(numBonuses):
            bonuses.append(resultsFb.Bonuses(i))

        return BattleResults(
                monstersDefeated = monstersDefeated,
                bonuses = bonuses,
                reward = resultsFb.Reward(),
                timeSecs = resultsFb.TimeSecs())

@dataclass(frozen=True)
class BattleCalcResults:
    fb: BattleCalcResultsFb
    results: BattleResults

@attr.s(frozen=True, auto_attribs=True)
class Battle:
    name: str
    attackerName: str
    defenderName: str
    events: List[BattleEvent]
    results: BattleResults

    def encodeEventsFb(self) -> bytearray:
        builder = flatbuffers.Builder(1024)
        fbEventOffsets = [event.toFb(builder) for event in reversed(self.events)]

        numEvents = len(self.events)
        BattleEventsFb.BattleEventsFbStartEventsVector(builder, numEvents)
        for fbEventOffset in fbEventOffsets:
            builder.PrependUOffsetTRelative(fbEventOffset)
        eventsVector = builder.EndVector()

        BattleEventsFb.BattleEventsFbStart(builder)
        BattleEventsFb.BattleEventsFbAddEvents(builder, eventsVector)
        battleEventsFb = BattleEventsFb.BattleEventsFbEnd(builder)
        builder.Finish(battleEventsFb)
        return builder.Output()

    def encodeEvents(self) -> str:
        return json.dumps(cattr.unstructure(self.events))

    def encodeResultsFb(self) -> bytearray:
        return self.results.encodeFb()

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

    @staticmethod
    def decodeEventsFb(encodedBytes: bytearray, offset: int = 0) -> List[BattleEvent]:
        eventsObj = BattleEventsFb.BattleEventsFb.GetRootAsBattleEventsFb(encodedBytes, offset)
        return Battle.fbToEvents(eventsObj)

    @staticmethod
    def fbToEvents(eventsObj: BattleEventsFb) -> List[BattleEvent]:
        numEvents = eventsObj.EventsLength()
        decodedEvents = []
        for i in range(numEvents):
            battleEvent = eventsObj.Events(i)
            battleEventUnionType = battleEvent.EventType()
            if battleEventUnionType == BattleEventUnionFb.BattleEventUnionFb().Move:
                moveEvent = MoveEventFb.MoveEventFb()
                moveEvent.Init(battleEvent.Event().Bytes, battleEvent.Event().Pos)
                decodedEvents.append(MoveEvent.fromFb(moveEvent))
            elif battleEventUnionType == BattleEventUnionFb.BattleEventUnionFb().Delete:
                deleteEvent = DeleteEventFb.DeleteEventFb()
                deleteEvent.Init(battleEvent.Event().Bytes, battleEvent.Event().Pos)
                decodedEvents.append(DeleteEvent.fromFb(deleteEvent))
            elif battleEventUnionType == BattleEventUnionFb.BattleEventUnionFb().Damage:
                damageEvent = DamageEventFb.DamageEventFb()
                damageEvent.Init(battleEvent.Event().Bytes, battleEvent.Event().Pos)
                decodedEvents.append(DamageEvent.fromFb(damageEvent))
        return decodedEvents
