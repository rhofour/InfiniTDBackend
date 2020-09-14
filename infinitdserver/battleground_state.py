from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import NewType, List, Optional, Dict, Any

from dataclasses_json import dataclass_json

from infinitdserver.game_config import GameConfig

TowerId = NewType('TowerId', int)

@dataclass_json
@dataclass
class BgTowerState:
    id: TowerId

@dataclass_json
@dataclass
class BgTowersState:
    towers: List[List[Optional[BgTowerState]]]

    @staticmethod
    def empty(rows: int, cols: int) -> BgTowersState:
        towers = [[None for col in range(cols)] for row in range(rows)]
        return BgTowersState(towers = towers)

@dataclass_json
@dataclass
class BattlegroundState:
    towers: BgTowersState

    @staticmethod
    def empty(gameConfig: GameConfig) -> BattlegroundState:
        towers = BgTowersState.empty(gameConfig.playfield.numRows, gameConfig.playfield.numCols)
        return BattlegroundState(towers = towers)
