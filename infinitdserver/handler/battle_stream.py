from infinitdserver.game import Game
from infinitdserver.handler.sse import SseStreamHandler

class BattleStreamHandler(SseStreamHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def initialize(self, game: Game):
        super(BattleStreamHandler, self).initialize(game)
        self.queues = game.battleQueues

    async def initialState(self, name: str):
        self.logInfo(f"Attemting to stream battle: {name}")
        initialState = self.game.joinBattle(name)
        self.logInfo(f"Initial state: {initialState}")
        return initialState
