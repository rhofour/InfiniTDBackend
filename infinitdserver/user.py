from dataclasses import dataclass, asdict
from typing import List

from dataclasses_json import dataclass_json

from infinitdserver.game_config import ConfigId

@dataclass_json
@dataclass(frozen=True)
class User:
    name: str
    uid: str
    gold: int
    accumulatedGold: int
    goldPerMinute: int
    inBattle: bool
    wave: List[ConfigId]
