from dataclasses import dataclass, asdict
from typing import NewType, Tuple, Dict, Any

from dataclasses_json import dataclass_json

Row = NewType('Row', int)
Col = NewType('Col', int)
Url = NewType('Url', str)
ConfigId = NewType('ConfigId', int)

@dataclass_json
@dataclass(frozen=True)
class CellPos:
    row: Row
    col: Col

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

@dataclass_json
@dataclass(frozen=True)
class MiscConfig:
    sellMultiplier: float
    startingGold: int
    minGoldPerMinute: float
    fullWaveMultiplier: float

@dataclass_json
@dataclass(frozen=True)
class GameConfig:
    playfield: PlayfieldConfig
    tiles: Tuple[TileConfig, ...]
    towers: Tuple[TowerConfig, ...]
    monsters: Tuple[MonsterConfig, ...]
    misc: MiscConfig
