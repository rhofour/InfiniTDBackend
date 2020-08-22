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
class GameConfig:
    playfield: PlayfieldConfig
    tiles: Tuple[TileConfig, ...]
    towers: Tuple[TowerConfig, ...]
    monsters: Tuple[MonsterConfig, ...]

def getMockConfig() -> GameConfig:
    serverAddress = 'http://localhost:8794'

    tiles = (
        TileConfig(id = ConfigId(0), url = Url(serverAddress + '/static/CrappyGrass.png')),
        TileConfig(id = ConfigId(1), url = Url(serverAddress + '/static/CrappyDirt.png')),
    )

    playfield = PlayfieldConfig(
        numCols = 10,
        numRows = 14,
        monsterEnter = CellPos(row = Row(0), col = Col(0)),
        monsterExit = CellPos(row = Row(9), col = Col(0)),
    )

    monsters = ()

    towers = (
        TowerConfig(
            id = ConfigId(0),
            url = Url(serverAddress + '/static/CrappyTowerSmall.png'),
            name = 'Boring Tower',
            cost = 1.0,
            firingRate = 2.0,
            range = 300.0,
            damage = 5.0,
        ),
        TowerConfig(
            id = ConfigId(1),
            url = Url(serverAddress + '/static/CrappyTower.png'),
            name = 'Better Tower',
            cost = 5.0,
            firingRate = 2.5,
            range = 500.0,
            damage = 15.0,
        ),
    )

    gameConfig = GameConfig(playfield=playfield, tiles=tiles, towers=towers, monsters=monsters)
    print('Game config dict:', repr(gameConfig.to_dict()))

    return gameConfig
