import json

import tornado
import tornado.escape

from infinitd_server.game import Game, UserInBattleException, UserHasInsufficientGoldException
from infinitd_server.handler.base import BaseHandler

class BuildHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name: str, rowStr: str, colStr: str):
        try:
            row = int(rowStr)
            col = int(colStr)
        except ValueError:
            self.logWarn(f"Got invalid row ({rowStr}) or col ({colStr})")
            self.set_status(400) # Bad request
            return
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            self.logWarn(f"Error decoding: {self.request.body}")
            self.set_status(400) # Bad request
            return
        self.logInfo(f"Got request for build/{name}/{row}/{col} with data {data}")
        try:
            towerId = data["towerId"]
        except KeyError:
            self.logWarn(f"Missing towerId in data: {data}")
            self.set_status(400) # Bad request
            return

        with self.getMutableUser(expectedName=name) as user:
            # Check that the row and column are within the playfield
            if row < 0 or row >= self.game.gameConfig.playfield.numRows:
                self.logWarn(f"Got invalid build request for row {row} of {self.game.gameConfig.playfield.numRows}.")
                self.set_status(404) # Not found
                return
            if col < 0 or col >= self.game.gameConfig.playfield.numCols:
                self.logWarn(f"Got invalid build request for col {col} of {self.game.gameConfig.playfield.numCols}.")
                self.set_status(404) # Not found
                return

            try:
                self.game.buildTower(user = user, row = row, col = col, towerId = towerId)
            except UserInBattleException as e:
                self.logInfo("BuildHandler error: " + repr(e))
                self.set_status(409) # Conflict
                self.write("Cannot build while in battle.")
                return
            except UserHasInsufficientGoldException as e:
                self.logInfo("BuildHandler error: " + repr(e))
                self.set_status(409) # Conflict
                self.write("Insufficient gold to build tower.")
                return
            except ValueError as e:
                self.logWarn("BuildHandler error: " + repr(e))
                self.set_status(409) # Conflict
                self.write(str(e))
                return

        self.set_status(201) # CREATED
