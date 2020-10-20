from infinitdserver.game import Game
from infinitdserver.handler.sse import SseStreamHandler

class BattlegroundStreamHandler(SseStreamHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def initialize(self, game: Game):
        super(BattlegroundStreamHandler, self).initialize(game)
        self.queues = game.battlegroundQueues

    async def initialState(self, name):
        return self.game.getBattleground(name)
