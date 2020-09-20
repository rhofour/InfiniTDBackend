import json

import tornado

from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.game_config import GameConfig
from infinitdserver.handler.base import BaseDbHandler

class SellHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    gameConfig: GameConfig

    def initialize(self, db, gameConfig):
        super(SellHandler, self).initialize(db)
        self.gameConfig = gameConfig

    async def delete(self, name: str, rowStr: str, colStr: str):
        row = int(rowStr)
        col = int(colStr)
        print(f"Got request for sell/{name}/{row}/{col}")

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got sell request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        # Check that the row and column are within the playfield
        if row < 0 or row >= self.gameConfig.playfield.numRows:
            print(f"Got invalid sell request for row {row} of {self.gameConfig.playfield.numRows}.")
            self.set_status(404) # Not found
            return
        if col < 0 or col >= self.gameConfig.playfield.numCols:
            print(f"Got invalid sell request for col {col} of {self.gameConfig.playfield.numCols}.")
            self.set_status(404) # Not found
            return

        try:
            await self.db.sellTower(name=name, row=row, col=col)
        except (ValueError, UserInBattleException)  as e:
            print("SellHandler error: " + repr(e))
            self.set_status(404) # Not found
            self.write(str(e))
            return

        self.set_status(200) # OK
