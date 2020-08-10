from dataclasses import dataclass, field
from typing import NewType, List, Optional

from common import Id
from game_config import GameConfig

@dataclass
class BackgroundState:
    ids: List[List[Id]]

@dataclass
class TowerState:
    id: Id

@dataclass
class TowersState:
    towers: List[List[Optional[TowerState]]]

@dataclass
class GameState:
    background: BackgroundState
    towers: TowersState
    gameConfig: InitVar[GameConfig]

    def __post_init__(self, gameConfig: GameConfig):
        self.validate(gameConfig):


    def validate(self, gameConfig: GameConfig):
        """Check this is a valid state for the given GameConfig."""
        rows = gameConfig.playfield.numRows
        cols = gameConfig.playfield.numCols
        
        checkListSize('Background', self.background.ids, rows, cols)
        checkListSize('Towers', self.towers.towers, rows, cols)

# Helper functions
def checkListSize(name: string, xs: List, rows: int, cols: int):
    if len(xs) != rows:
        raise Exception(f'{name} has {len(xs)} rows, but game config expects {rows}.')
    for (i, row) in enumerate(xs):
        if len(row) != cols:
            raise Exception(f'{name}, row {i} has {len(row)} columns, but game config expects {cols}.')
