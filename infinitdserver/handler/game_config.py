from infinitdserver.game_config import GameConfig
from infinitdserver.handler.base import BaseHandler

class GameConfigHandler(BaseHandler):
    gameConfig: GameConfig

    def initialize(self, gameConfig):
        self.gameConfig = gameConfig

    def get(self):
        self.write(self.gameConfig.to_dict())
