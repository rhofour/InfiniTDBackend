from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum, unique, auto
from typing import NewType, Tuple, Dict, List

import attr
import cattr
from dataclasses_json import dataclass_json

Row = NewType('Row', int)
Col = NewType('Col', int)
Url = NewType('Url', str)
ConfigId = NewType('ConfigId', int)
cattr.register_structure_hook(ConfigId, lambda d, _: ConfigId(d))

@dataclass_json
@dataclass(frozen=True)
class CellPos:
    row: Row
    col: Col

    def toNumber(self, numCols: int) -> int:
        return self.row * numCols + self.col;

    @staticmethod
    def fromNumber(number: int, numCols: int) -> CellPos:
        return CellPos(number // numCols, number % numCols)

@dataclass_json
@dataclass(frozen=True)
class PlayfieldConfig:
    numRows: int
    numCols: int
    monsterEnter: CellPos
    monsterExit: CellPos
    backgroundId: int
    pathId: int
    pathStartId: int
    pathEndId: int

@dataclass(frozen=True)
class IdentifiedImage:
    id: ConfigId
    url: Url

@dataclass(frozen=True)
class TileConfig(IdentifiedImage):
    pass

@dataclass_json
@dataclass(frozen=True)
class TowerConfig(IdentifiedImage):
    name: str
    cost: float
    firingRate: float
    range: float
    damage: float

@dataclass_json
@dataclass(frozen=True)
class MonsterConfig(IdentifiedImage):
    name: str
    health: float
    speed: float
    bounty: float

MonstersDefeated = Dict[ConfigId, Tuple[int, int]]

@unique
class BonusType(Enum):
    ADDITIVE = auto()
    MULTIPLICATIVE = auto()

@attr.s(frozen=True, auto_attribs=True)
class BonusCondition:
    percentDefeated: Optional[float]

@attr.s(frozen=True, auto_attribs=True)
class BattleBonus:
    name: str
    bonusType: BonusType
    bonusAmount: float
    conditions: List[BonusCondition]

    def isEarned(self, monstersDefeated: MonstersDefeated) -> bool:
        totalMonsters = 0
        totalNumDefeated = 0

        for (monsterId, (numDefeated, numSent)) in monstersDefeated.items():
            totalMonsters += numSent
            totalNumDefeated += numDefeated
        percentDefeated = totalNumDefeated / totalMonsters * 100 if totalMonsters > 0 else -1

        for condition in self.conditions:
            if (condition.percentDefeated is not None and
                    condition.percentDefeated > percentDefeated):
                return False
        return True

    def getAmount(self, curGold: float) -> float:
        if self.bonusType == BonusType.ADDITIVE:
            return self.bonusAmount;
        if self.bonusType == BonusType.MULTIPLICATIVE:
            return curGold * (self.bonusAmount - 1);
        raise ValueError(f"Unknown bonus type: {self.bonusType}")


@dataclass_json
@dataclass(frozen=True)
class MiscConfig:
    sellMultiplier: float
    startingGold: int
    minGoldPerMinute: float
    battleBonuses: List[BattleBonus]

@dataclass_json
@dataclass(frozen=True)
class GameConfig:
    playfield: PlayfieldConfig
    tiles: Tuple[TileConfig, ...]
    towers: Tuple[TowerConfig, ...]
    monsters: Tuple[MonsterConfig, ...]
    misc: MiscConfig
