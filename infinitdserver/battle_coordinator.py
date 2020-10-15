import asyncio
from typing import List, Dict, Union, Callable, Deque, Awaitable

from collections import deque
import time

from infinitdserver.battle import BattleComputer, BattleEvent
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger

class StreamingBattle:
    """StreamingBattle handles streaming battle data out in "real time"
    to potentially multiple clients."""
    BUFFER_TIME_SECS: float = 0.1
    startTime: float = -1.0 # -1 signifies the battle hasn't started yet
    pastEvents: List[BattleEvent] = []
    futureEvents: Deque[BattleEvent]
    updateFn: Callable[[Union[float, BattleEvent]], Awaitable[None]]

    def __init__(self, updateFn: Callable[[Union[float, BattleEvent]], Awaitable[None]]):
        self.updateFn = updateFn

    async def start(self, events: List[BattleEvent]):
        if not events:
            return # Do nothing if events is empty
        self.futureEvents = deque(events)
        self.pastEvents = []

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
        await self.updateFn(0.0)

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
        await self.updateFn(-1.0) # Send an update to halt the battle.

    def join(self) -> List[Union[BattleEvent, float]]:
        """Send the new client all past events and the current time."""
        if self.startTime == -1.0:
            return [-1.0]
        else:
            battleTime = time.time() - self.startTime
            return self.pastEvents + [battleTime]

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

    def startBattle(self, name: str, events: List[BattleEvent], callback: Callable[[], Awaitable[None]],
            handler: str = "BattleCoordinator", requestId = -1):
        if name not in self.battles:
            self.logger.info(handler, requestId, f"Coordinator is making a new StreamingBattle for {name}")
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        self.logger.info(handler, requestId, f"Coordinator is starting a StreamingBattle for {name}")
        async def startBattleThenCallCallback():
            await self.battles[name].start(events)
            await callback()
        loop = asyncio.get_running_loop()
        loop.create_task(startBattleThenCallCallback())

    def stopBattle(self, name: str, callback: Callable[[], Awaitable[None]],
            handler: str = "BattleCoordinator", requestId = -1):
        loop = asyncio.get_running_loop()
        if name in self.battles:
            async def stopBattleThenCallCallback():
                await self.battles[name].stop()
                await callback()
            loop.create_task(stopBattleThenCallCallback())
        else:
            loop.create_task(callback())
