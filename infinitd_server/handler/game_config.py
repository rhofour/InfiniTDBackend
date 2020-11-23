import json

import cattr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class GameConfigHandler(BaseHandler):
    game: Game

    def get(self):
        self.write(json.dumps(cattr.unstructure(self.game.gameConfig.gameConfigData)))
