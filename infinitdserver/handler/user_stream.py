from infinitdserver.game import Game
from infinitdserver.sse import SseQueues
from infinitdserver.handler.sse import SseStreamHandler

class UserStreamHandler(SseStreamHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def initialize(self, game: Game):
        self.game = game
        self.queues = game.userQueues

    async def initialState(self, name):
        return self.game.getUserSummaryByName(name)
