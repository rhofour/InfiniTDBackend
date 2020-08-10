from dataclasses import dataclass
from typing import NewType, List, Optional

from dataclasses_json import dataclass_json

TowerId = NewType('TowerId', int)

@dataclass_json
@dataclass
class BattlegroundState:
    towers: List[List[Optional[TowerId]]]
