from dataclasses import dataclass, asdict

from dataclasses_json import dataclass_json

@dataclass_json
@dataclass(frozen=True)
class User:
    name: str
    gold: int
    accumulatedGold: int
    goldPerMinute: int
    inBattle: bool
