from dataclasses import dataclass, asdict
from typing import NewType, List, Optional, Dict, Any

from dataclasses_json import dataclass_json

TowerId = NewType('TowerId', int)

@dataclass_json
@dataclass
class BgTowerState:
    id: TowerId

@dataclass_json
@dataclass
class BgTowersState:
    towers: List[List[Optional[BgTowerState]]]

@dataclass_json
@dataclass
class BattlegroundState:
    towers: BgTowersState

    def toDict(self) -> Dict[str, Any]:
        return asdict(self)
