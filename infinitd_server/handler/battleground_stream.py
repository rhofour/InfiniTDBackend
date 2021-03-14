from infinitd_server.game import Game
from infinitd_server.handler.sse import SseStreamHandler

class BattlegroundStreamHandler(SseStreamHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def initialize(self, game: Game):
        super(BattlegroundStreamHandler, self).initialize(game)
        self.queues = game.queues["battleground"]

    async def initialState(self, name):
        return self.game.getBattleground(name)
