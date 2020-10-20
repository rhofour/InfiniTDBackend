from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class GameConfigHandler(BaseHandler):
    game: Game

    def get(self):
        self.write(self.game.gameConfig.to_dict())
