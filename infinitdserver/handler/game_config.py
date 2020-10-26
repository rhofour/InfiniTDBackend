import json

import cattr

from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class GameConfigHandler(BaseHandler):
    game: Game

    def get(self):
        self.write(json.dumps(cattr.unstructure(self.game.gameConfig.gameConfigData)))
