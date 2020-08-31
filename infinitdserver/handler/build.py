import tornado

from infinitdserver.db import Db
from infinitdserver.game_config import GameConfig
from infinitdserver.handler.base import BaseDbHandler

class BuildHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    gameConfig: GameConfig

    def initialize(self, db, gameConfig):
        super(BuildHandler, self).initialize(db)
        self.gameConfig = gameConfig

    def post(self, name: str, rowStr: str, colStr: str):
        row = int(rowStr)
        col = int(colStr)
        data = tornado.escape.json_decode(self.request.body)
        print(f"Got request for build/{name}/{row}/{col} with data {data}")
        towerId = data["towerId"]
        decoded_token = self.verifyAuthentication()

        # Check that the name matches the authorized user
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got build request for {name} from {user.name}.")
            self.set_status(403); # Forbidden
            return

        # Check that the row and column are within the playfield

        # Check that there's no existing tower there

        # Check that the player has sufficient gold

        self.set_status(201); # CREATED
