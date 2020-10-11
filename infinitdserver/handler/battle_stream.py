from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.db import Db
from infinitdserver.sse import SseQueues
from infinitdserver.handler.sse import SseStreamHandler

class BattleStreamHandler(SseStreamHandler):
    db: Db
    queues: SseQueues
    battleCoordinator: BattleCoordinator

    def initialize(self, db: Db, queues: SseQueues, battleCoordinator: BattleCoordinator):
        self.db = db
        self.queues = queues
        self.battleCoordinator = battleCoordinator

    async def initialState(self, name):
        self.logInfo(f"Attemting to stream battle: {name}")
        initialState = self.battleCoordinator.getBattle(name).join()
        self.logInfo(f"Initial state: {initialState}")
        return initialState
