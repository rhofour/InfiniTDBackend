import asyncio
from collections import deque
from dataclasses import dataclass
from enum import Enum, unique, auto
import time
from typing import List, Dict, Union, Callable, Deque, Awaitable, Optional

from dataclasses_json import dataclass_json

from infinitd_server.battle import Battle, BattleEvent, BattleResults
from infinitd_server.sse import SseQueues
from infinitd_server.logger import Logger

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
    attackerName: str = ""
    defenderName: str = ""

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
    name: str = ""
    attackerName: str = ""
    defenderName: str = ""
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

    async def start(self, battle: Battle, resultsCallback: Callable[[BattleResults], None], requestId: int = -1):
        if not battle.events:
            return # Do nothing if events is empty
        self.logger.info("BattleCoordinator", requestId, f"Starting battle {battle.name} with {len(battle.events)} events")
        self.futureEvents = deque(battle.events)
        self.pastEvents = []
        self.name = battle.name
        self.attackerName = battle.attackerName
        self.defenderName = battle.defenderName
        self.sentUpdates = 0

        # Let the client know a new battle is coming.
        await self.sendUpdate(BattleMetadata(
            status = BattleStatus.PENDING, name = battle.name,
            attackerName = battle.attackerName, defenderName = battle.defenderName))

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
        await self.sendUpdate(LiveBattleMetadata(
            status = BattleStatus.LIVE, name = battle.name, time = 0.0,
            attackerName = battle.attackerName, defenderName = battle.defenderName))

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

        # Prevent new listeners from getting all the events now that the battle
        # is over.
        self.startTime = -1.0

        expectedBattleUpdates = len(battle.events) + 2 # Two extra for pending and live metadata events
        if (self.sentUpdates > expectedBattleUpdates):
            self.logger.error("BattleCoordinator", requestId,
                    f"Battle had {len(battle.events)} events, but sent {self.sentUpdates} updates.")
        elif (self.sentUpdates == expectedBattleUpdates):
            # This means the battle ran all the way out.
            resultsCallback(battle.results)
            await self.updateFn(battle.results)
        else:
            # Stop the battle without sending results.
            await self.sendUpdate(BattleMetadata(
                status = BattleStatus.PENDING, name = battle.name,
                attackerName = battle.attackerName, defenderName = battle.defenderName))

    async def stop(self):
        self.startTime = -1.0
        self.futureEvents = deque()
        # Send an update to halt the battle.
        await self.updateFn(BattleMetadata(
            status = BattleStatus.PENDING, name = self.name,
            attackerName = self.attackerName, defenderName = self.defenderName)) 

    def join(self) -> List[Union[BattleEvent, BattleMetadata]]:
        """Send the new client all past events and the current time."""
        if self.startTime == -1.0:
            return [BattleMetadata(
                status = BattleStatus.PENDING, name = self.name,
                attackerName = self.attackerName, defenderName = self.defenderName)]
        else:
            battleTime = time.time() - self.startTime
            return self.pastEvents + [LiveBattleMetadata(
                status = BattleStatus.LIVE, time = battleTime, name = self.name,
                attackerName = self.attackerName, defenderName = self.defenderName)]

class BattleCoordinator:
    battles: Dict[str, StreamingBattle] = {}
    battleQueues: SseQueues

    def __init__(self, battleQueues: SseQueues):
        self.battleQueues = battleQueues
        self.logger = Logger.getDefault()

    def getBattle(self, name: str):
        if name not in self.battles:
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        return self.battles[name]

    def startBattle(self, name: str, battle: Battle, resultsCallback: Callable[[BattleResults], None],
            endCallback: Callable[[], None], handler: str = "BattleCoordinator", requestId = -1):
        """startBattle triggers the start of a live-streamed battle.

        Arguments:
        name: str -- The name of the battle.
        battle: Battle -- The battle to stream.
        resultsCallback: Callable[[BattleResults], None] -- A callback to handle the results of a completed battle.
        endCallback: Callable[[], None] -- A callback called whenever a battle ends whether it's completed or not.
        """
        if name not in self.battles:
            self.logger.info(handler, requestId, f"Coordinator is making a new StreamingBattle for {name}")
            self.battles[name] = StreamingBattle(lambda x: self.battleQueues.sendUpdate(name, x))
        self.logger.info(handler, requestId, f"Coordinator is starting a StreamingBattle for {name}")
        async def startBattleThenCallCallback():
            await self.battles[name].start(battle, resultsCallback = resultsCallback, requestId = requestId)
            endCallback()
        loop = asyncio.get_running_loop()
        loop.create_task(startBattleThenCallCallback())

    async def stopBattle(self, name: str):
        if name in self.battles:
            await self.battles[name].stop()
