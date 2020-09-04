from infinitdserver.db import Db
from infinitdserver.sse import SseStreamHandler, SseQueues

class UserStreamHandler(SseStreamHandler):
    db: Db
    queues: SseQueues

    def initialize(self, db, queues):
        self.db = db
        self.queues = queues

    async def initialState(self, name):
        return self.db.getUserByName(name)