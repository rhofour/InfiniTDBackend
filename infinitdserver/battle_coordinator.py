from typing import List, Dict, Union, Callable, Deque

from collections import deque
import time

from infinitdserver.battle import BattleComputer, BattleEvent
from infinitdserver.sse import SseQueues

class StreamingBattle:
    """StreamingBattle handles streaming battle data out in "real time"
    to potentially multiple clients."""
    startTime: float = -1.0 # -1 signifies the battle hasn't started yet
    pastEvents: List[BattleEvent] = []
    futureEvents: Deque[BattleEvent]
    updateFn: Callable[[Union[float, BattleEvent]], None]

    def __init__(self, updateFn: Callable[[Union[float, BattleEvent]], None]):
        self.updateFn = updateFn

    def start(self, events: List[BattleEvent]):
        self.startTime = time.time()
        self.futureEvents = deque(events)

    def stop(self):
        self.startTime = -1.0
        self.pastEvents = []
        updateFn(-1.0) # Send an update to halt the battle.

    def join(self) -> List[Union[BattleEvent, float]]:
        """Send the new client all past events and the current time."""
        if startTime == -1.0:
            return [-1.0]
        else:
            battleTime = time.time() - startTime
            return self.pastEvents + [battleTime]

class BattleCoordinator:
    battleComputer: BattleComputer
    battles: Dict[str, StreamingBattle] = {}
    battleQueues: SseQueues

    def __init__(self, battleQueues: SseQueues):
        self.battleQueues = battleQueues

    def getBattle(self, name: str):
        if name not in battlesInProgress:
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        return battles[name]
