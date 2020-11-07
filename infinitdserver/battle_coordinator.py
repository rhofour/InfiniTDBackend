import asyncio
from collections import deque
from dataclasses import dataclass
from enum import Enum, unique, auto
import time
from typing import List, Dict, Union, Callable, Deque, Awaitable, Optional

from dataclasses_json import dataclass_json

from infinitdserver.battle import Battle, BattleEvent, BattleResults
from infinitdserver.battle_computer import BattleComputer
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger

@unique
class BattleStatus(Enum):
    PENDING = auto()
    FINISHED = auto()
    LIVE = auto()

@dataclass_json
@dataclass(frozen=False)
class BattleMetadata:
    status: BattleStatus
    name: str = ""

@dataclass_json
@dataclass(frozen=False)
class LiveBattleMetadata(BattleMetadata):
    time: float = 0.0

BattleUpdate = Union[BattleMetadata, BattleEvent, BattleResults]

class StreamingBattle:
    """StreamingBattle handles streaming battle data out in "real time"
    to potentially multiple clients."""
    BUFFER_TIME_SECS: float = 0.1
    startTime: float = -1.0 # -1 signifies the battle hasn't started yet
    name : str = ""
    pastEvents: List[BattleEvent] = []
    futureEvents: Deque[BattleEvent]
    updateFn: Callable[[BattleUpdate], Awaitable[None]]
    sentUpdates : int = 0

    def __init__(self, updateFn: Callable[[BattleUpdate], Awaitable[None]]):
        self.updateFn = updateFn
        self.logger = Logger.getDefault()

    async def sendUpdate(self, update: BattleUpdate):
        await self.updateFn(update)
        self.sentUpdates += 1

    async def start(self, battle: Battle, requestId: int = -1):
        if not battle.events:
            return # Do nothing if events is empty
        self.logger.info("BattleCoordinator", requestId, f"Starting battle {battle.name} with {len(battle.events)} events")
        self.futureEvents = deque(battle.events)
        self.pastEvents = []
        self.name = battle.name
        self.sentUpdates = 0

        # Let the client know a new battle is coming.
        await self.sendUpdate(BattleMetadata(status = BattleStatus.PENDING, name = battle.name))

        # Send all events occurring in the buffer window
        numInitialEvents = 0
        for event in self.futureEvents:
            if event.startTime > self.BUFFER_TIME_SECS:
                break
            await self.sendUpdate(event)
            numInitialEvents += 1

        # Move the initial events from futureEvents to the pastEvents
        while numInitialEvents:
            self.pastEvents.append(self.futureEvents.popleft())
            numInitialEvents -= 1

        # Start running
        self.startTime = time.time()
        await self.sendUpdate(LiveBattleMetadata(status = BattleStatus.LIVE, name = battle.name, time = 0.0))

        while self.futureEvents:
            elapsedTime = time.time() - self.startTime
            event: BattleEvent = self.futureEvents[0]
            timeToEvent = event.startTime - elapsedTime
            if timeToEvent < 0:
                # We've fallen behind which should never happen.
                self.logger.error("BattleCoordinator", requestId, f"Found negative timeToEvent: {timeToEvent}")
            if timeToEvent > self.BUFFER_TIME_SECS:
                await asyncio.sleep(timeToEvent - self.BUFFER_TIME_SECS + 0.0001)
                continue

            # Send the event
            await self.sendUpdate(event)
            self.pastEvents.append(self.futureEvents.popleft())

        if (self.sentUpdates != len(battle.events) + 2): # Two extra for the metadata
            self.logger.error("BattleCoordinator", requestId,
                    f"Battle had {len(battle.events)} events, but sent {self.sentUpdates} updates.")
        await self.sendResults(battle.results)

    async def sendResults(self, results: BattleResults):
        await self.updateFn(results)
        self.startTime = -1.0
        self.futureEvents = deque()
        self.pastEvents = []

    async def stop(self):
        self.startTime = -1.0
        self.futureEvents = deque()
        self.pastEvents = []
        await self.updateFn(BattleMetadata(status = BattleStatus.PENDING, name = self.name)) # Send an update to halt the battle.

    def join(self) -> List[Union[BattleEvent, BattleMetadata]]:
        """Send the new client all past events and the current time."""
        if self.startTime == -1.0:
            return [BattleMetadata(status = BattleStatus.PENDING, name = self.name)]
        else:
            battleTime = time.time() - self.startTime
            return self.pastEvents + [LiveBattleMetadata(status = BattleStatus.LIVE, time = battleTime, name = self.name)]

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
            await self.battles[name].start(battle, requestId)
            await callback()
        loop = asyncio.get_running_loop()
        loop.create_task(startBattleThenCallCallback())

    async def stopBattle(self, name: str):
        if name in self.battles:
            await self.battles[name].stop()
