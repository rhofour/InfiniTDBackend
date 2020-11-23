from infinitd_server.db import Db
from infinitd_server.sse import SseQueues
from infinitd_server.handler.sse import SseStreamHandler

class BattlegroundStateHandler(SseStreamHandler):
    db: Db
    queues: SseQueues

    def initialize(self, db, queues):
        self.db = db
        self.queues = queues

    async def initialState(self, name):
        return self.db.getBattleground(name)
