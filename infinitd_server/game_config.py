from dataclasses import dataclass, asdict
from enum import Enum, unique, auto
from typing import NewType, Tuple, Dict, List, Optional

import attr
import cattr

Row = NewType('Row', int)
Col = NewType('Col', int)
Url = NewType('Url', str)
ConfigId = NewType('ConfigId', int)
cattr.register_structure_hook(Row, lambda d, _: Row(d))
cattr.register_structure_hook(Col, lambda d, _: Col(d))
cattr.register_structure_hook(Url, lambda d, _: Url(d))
cattr.register_structure_hook(ConfigId, lambda d, _: ConfigId(d))

@attr.s(frozen=True, auto_attribs=True)
class CellPos:
    row: Row
    col: Col

    def toNumber(self, numCols: int) -> int:
        return self.row * numCols + self.col;

    def toTuple(self) -> Tuple[int, int]:
        return (self.row, self.col)

    @staticmethod
    def fromNumber(number: int, numCols: int):
        return CellPos(Row(number // numCols), Col(number % numCols))

    @staticmethod
    def fromTuple(t: Tuple[int, int]):
        return CellPos(Row(t[0]), Col(t[1]))

@attr.s(frozen=True, auto_attribs=True)
class PlayfieldConfig:
    numRows: int
    numCols: int
    monsterEnter: CellPos
    monsterExit: CellPos
    # Playfield tile details.
    backgroundId: int
    pathId: int
    pathStartId: int
    pathEndId: int
    tileSize: int

@attr.s(frozen=True, auto_attribs=True)
class IdentifiedImage:
    id: ConfigId
    url: Url

@attr.s(frozen=True, auto_attribs=True)
class TileConfig(IdentifiedImage):
    pass

@attr.s(frozen=True, auto_attribs=True)
class ProjectileConfig(IdentifiedImage):
    size: int

@attr.s(frozen=True, auto_attribs=True)
class TowerConfig(IdentifiedImage):
    name: str
    cost: float
    firingRate: float
    range: float
    damage: float
    projectileSpeed: float
    projectileId: ConfigId

@attr.s(frozen=True, auto_attribs=True)
class MonsterConfig(IdentifiedImage):
    name: str
    health: float
    speed: float
    bounty: float
    size: float

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
    id: ConfigId
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

    def getAmount(self, curReward: float) -> float:
        if self.bonusType == BonusType.ADDITIVE:
            return self.bonusAmount;
        if self.bonusType == BonusType.MULTIPLICATIVE:
            return curReward * (self.bonusAmount - 1);
        raise ValueError(f"Unknown bonus type: {self.bonusType}")

def idedListToDict(xs):
    d = {}
    for x in xs:
        if x.id in d:
            raise ValueError(f"Found duplicated id {x.id}")
        d[x.id] = x
    return d

@attr.s(frozen=True, auto_attribs=True)
class MiscConfigData:
    sellMultiplier: float
    startingGold: int
    minGoldPerMinute: float
    battleBonuses: List[BattleBonus]

@dataclass(frozen=True)
class MiscConfig:
    sellMultiplier: float
    startingGold: int
    minGoldPerMinute: float
    battleBonuses: Dict[ConfigId, BattleBonus]

    @staticmethod
    def fromMiscConfigData(miscConfigData: MiscConfigData):
        return MiscConfig(
            sellMultiplier = miscConfigData.sellMultiplier,
            startingGold = miscConfigData.startingGold,
            minGoldPerMinute = miscConfigData.minGoldPerMinute,
            battleBonuses = idedListToDict(miscConfigData.battleBonuses)
        )

@attr.s(frozen=True, auto_attribs=True)
class GameConfigData:
    playfield: PlayfieldConfig
    tiles: List[TileConfig]
    towers: List[TowerConfig]
    projectiles: List[ProjectileConfig]
    monsters: List[MonsterConfig]
    misc: MiscConfigData

@dataclass(frozen=True)
class GameConfig:
    playfield: PlayfieldConfig
    tiles: Dict[ConfigId, TileConfig]
    towers: Dict[ConfigId, TowerConfig]
    projectiles: Dict[ConfigId, ProjectileConfig]
    monsters: Dict[ConfigId, MonsterConfig]
    misc: MiscConfig
    gameConfigData: GameConfigData

    @staticmethod
    def fromGameConfigData(gameConfigData: GameConfigData):
        return GameConfig(
            playfield = gameConfigData.playfield,
            tiles = idedListToDict(gameConfigData.tiles),
            towers = idedListToDict(gameConfigData.towers),
            projectiles = idedListToDict(gameConfigData.projectiles),
            monsters = idedListToDict(gameConfigData.monsters),
            misc = MiscConfig.fromMiscConfigData(gameConfigData.misc),
            gameConfigData = gameConfigData
        )
