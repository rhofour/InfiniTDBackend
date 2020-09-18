from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.db import Db
from infinitdserver.sse import SseStreamHandler, SseQueues

class BattleStreamHandler(SseStreamHandler):
    db: Db
    queues: SseQueues
    battleCoordinator: BattleCoordinator

    def initialize(self, db: Db, queues: SseQueues, battleCoordinator: BattleCoordinator):
        self.db = db
        self.queues = queues
        self.battleCoordinator = BattleCoordinator

    async def initialState(self, name):
        return battleCoordinator.getBattle(name).join()
