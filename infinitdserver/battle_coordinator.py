import asyncio
from collections import deque
from dataclasses import dataclass
import time
from typing import List, Dict, Union, Callable, Deque, Awaitable

from dataclasses_json import dataclass_json

from infinitdserver.battle import Battle, BattleComputer, BattleEvent
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger

@dataclass_json
@dataclass(frozen=False)
class StartBattle:
    time: float
    name: str

class StreamingBattle:
    """StreamingBattle handles streaming battle data out in "real time"
    to potentially multiple clients."""
    BUFFER_TIME_SECS: float = 0.1
    startTime: float = -1.0 # -1 signifies the battle hasn't started yet
    name : str
    pastEvents: List[BattleEvent] = []
    futureEvents: Deque[BattleEvent]
    updateFn: Callable[[Union[StartBattle, BattleEvent]], Awaitable[None]]

    def __init__(self, updateFn: Callable[[Union[StartBattle, BattleEvent]], Awaitable[None]]):
        self.updateFn = updateFn

    async def start(self, battle: Battle):
        if not battle.events:
            return # Do nothing if events is empty
        self.futureEvents = deque(battle.events)
        self.pastEvents = []
        self.name = battle.name

        # Send all events occurring in the buffer window
        numInitialEvents = 0
        for event in self.futureEvents:
            if event.startTime > self.BUFFER_TIME_SECS:
                break
            await self.updateFn(event)
            numInitialEvents += 1

        # Move the initial events from futureEvents to the pastEvents
        while numInitialEvents:
            self.pastEvents.append(self.futureEvents.popleft())
            numInitialEvents -= 1

        # Start running
        self.startTime = time.time()
        await self.updateFn(StartBattle(time = 0.0, name = battle.name))

        while self.futureEvents:
            elapsedTime = time.time() - self.startTime
            event: BattleEvent = self.futureEvents[0]
            timeToEvent = event.startTime - elapsedTime
            if timeToEvent > self.BUFFER_TIME_SECS:
                await asyncio.sleep(timeToEvent - self.BUFFER_TIME_SECS + 0.0001)
                continue

            # Send the event
            await self.updateFn(event)
            self.pastEvents.append(self.futureEvents.popleft())

        await self.stop()

    async def stop(self):
        self.startTime = -1.0
        self.futureEvents = deque()
        self.pastEvents = []
        await self.updateFn(StartBattle(time = -1.0, name = "")) # Send an update to halt the battle.

    def join(self) -> List[Union[BattleEvent, StartBattle]]:
        """Send the new client all past events and the current time."""
        if self.startTime == -1.0:
            return [StartBattle(time = -1.0, name = "")]
        else:
            battleTime = time.time() - self.startTime
            return self.pastEvents + [StartBattle(time = battleTime, name = self.name)]

class BattleCoordinator:
    battleComputer: BattleComputer
    battles: Dict[str, StreamingBattle] = {}
    battleQueues: SseQueues

    def __init__(self, battleQueues: SseQueues):
        self.battleQueues = battleQueues
        self.logger = Logger.getDefault()

    def getBattle(self, name: str):
        if name not in self.battles:
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        return self.battles[name]

    def startBattle(self, name: str, battle: Battle, callback: Callable[[], Awaitable[None]],
            handler: str = "BattleCoordinator", requestId = -1):
        if name not in self.battles:
            self.logger.info(handler, requestId, f"Coordinator is making a new StreamingBattle for {name}")
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        self.logger.info(handler, requestId, f"Coordinator is starting a StreamingBattle for {name}")
        async def startBattleThenCallCallback():
            await self.battles[name].start(battle)
            await callback()
        loop = asyncio.get_running_loop()
        loop.create_task(startBattleThenCallCallback())

    async def stopBattle(self, name: str):
        if name in self.battles:
            await self.battles[name].stop()
