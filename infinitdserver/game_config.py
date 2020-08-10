from dataclasses import dataclass, asdict
from typing import NewType, Tuple, Dict, Any

from common import Row, Col, Url

ConfigId = NewType('ConfigId', int)

@dataclass(frozen=True)
class CellPos:
    row: Row
    col: Col

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class PlayfieldConfig:
    numRows: int
    numCols: int
    monsterEnter: CellPos
    monsterExit: CellPos

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class IdentifiedImage:
    id: ConfigId
    url: Url

@dataclass(frozen=True)
class TileConfig(IdentifiedImage):

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class TowerConfig(IdentifiedImage):
    name: str
    cost: float
    firingRate: float
    range: float
    damage: float

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class MonsterConfig(IdentifiedImage):
    name: str
    health: float
    speed: float
    bounty: float

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class GameConfig:
    playfield: PlayfieldConfig
    tiles: Tuple[TileConfig, ...]
    towers: Tuple[TowerConfig, ...]
    monsters: Tuple[MonsterConfig, ...]

    def toDict(self) -> Dict[str, Any]:
        out = asdict(self)
        out['hash'] = self.__hash__()
        return out

def getMockConfig() -> GameConfig:
    serverAddress = 'http://localhost:8794'

    tiles = (
        TileConfig(id = 0, url = serverAddress + '/static/CrappyGrass.png'),
        TileConfig(id = 1, url = serverAddress + '/static/CrappyDirt.png'),
    )

    playfield = PlayfieldConfig(
        numCols = 10,
        numRows = 14,
        monsterEnter = CellPos(row = 0, col = 0),
        monsterExit = CellPos(row = 9, col = 0),
    )

    monsters = ()

    towers = (
        TowerConfig(
            id = 0,
            url = serverAddress + '/static/CrappyTowerSmall.png',
            name = 'Boring Tower',
            cost = 1.0,
            firingRate = 2.0,
            range = 300.0,
            damage = 5.0,
        ),
        TowerConfig(
            id = 1,
            url = serverAddress + '/static/CrappyTower.png',
            name = 'Better Tower',
            cost = 5.0,
            firingRate = 2.5,
            range = 500.0,
            damage = 15.0,
        ),
    )

    gameConfig = GameConfig(playfield=playfield, tiles=tiles, towers=towers, monsters=monsters)
    print('Game config dict:', repr(gameConfig.toDict()))

    return gameConfig
