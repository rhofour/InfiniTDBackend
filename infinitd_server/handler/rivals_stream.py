from infinitd_server.game import Game
from infinitd_server.sse import SseQueues
from infinitd_server.handler.sse import SseStreamHandler

class RivalsStreamHandler(SseStreamHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def initialize(self, game: Game):
        self.game = game
        self.queues = game.rivalsQueues

    async def initialState(self, name):
        return self.game.getUserRivals(name)
