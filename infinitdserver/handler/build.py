import json

import tornado
import tornado.escape

from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.game_config import GameConfig
from infinitdserver.handler.base import BaseDbHandler

class BuildHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    gameConfig: GameConfig

    def initialize(self, db, gameConfig):
        super(BuildHandler, self).initialize(db)
        self.gameConfig = gameConfig

    async def post(self, name: str, rowStr: str, colStr: str):
        row = int(rowStr)
        col = int(colStr)
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            print(f"BuildHandler: Error decoding: {self.request.body}")
            self.set_status(400)
            return
        print(f"Got request for build/{name}/{row}/{col} with data {data}")
        try:
            towerId = data["towerId"]
        except KeyError:
            self.set_status(400)
            return

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got build request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        # Check that the row and column are within the playfield
        if row < 0 or row >= self.gameConfig.playfield.numRows:
            print(f"Got invalid build request for row {row} of {self.gameConfig.playfield.numRows}.")
            self.set_status(404) # Not found
            return
        if col < 0 or col >= self.gameConfig.playfield.numCols:
            print(f"Got invalid build request for col {col} of {self.gameConfig.playfield.numCols}.")
            self.set_status(404) # Not found
            return

        try:
            await self.db.buildTower(name=name, row=row, col=col, towerId=towerId)
        except (ValueError, UserInBattleException, UserHasInsufficientGoldException)  as e:
            print("BuildHandler error: " + str(e))
            self.set_status(409) # Conflict
            self.write(str(e))
            return

        self.set_status(201) # CREATED
