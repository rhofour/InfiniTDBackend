import json

import tornado

from infinitd_server.game import Game, UserInBattleException, UserHasInsufficientGoldException
from infinitd_server.handler.base import BaseHandler

class SellHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name: str):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            self.logWarn(f"Error decoding: {self.request.body}")
            self.set_status(400) # Bad request
            return
        self.logInfo(f"Got request for sell/{name} with data {data}")
        
        try:
            rows = data["rows"]
        except KeyError:
            self.logWarn(f"Missing rows in data: {data}")
            self.set_status(400) # Bad request
            return
        try:
            cols = data["cols"]
        except KeyError:
            self.logWarn(f"Missing cols in data: {data}")
            self.set_status(400) # Bad request
            return

        if len(rows) != len(cols):
            self.logWarn("rows and cols aren't the same length: {len(rows)}, {len(cols)}")
            self.set_status(400) # Bad request
            return

        with self.getMutableUser(expectedName=name) as user:
            try:
                self.game.sellTowers(user=user, rows=rows, cols=cols)
            except (ValueError, UserInBattleException)  as e:
                self.logInfo("SellHandler error: " + repr(e))
                self.set_status(400) # Bad request
                self.write(str(e))
                return

    def delete(self, name: str, rowStr: str, colStr: str):
        try:
            row = int(rowStr)
            col = int(colStr)
        except ValueError:
            self.logWarn(f"Got invalid row ({rowStr}) or col ({colStr})")
            self.set_status(400) # Bad request
            return
        self.logInfo(f"Got request for sell/{name}/{row}/{col}")

        with self.getMutableUser(expectedName=name) as user:
            # Check that the row and column are within the playfield
            if row < 0 or row >= self.game.gameConfig.playfield.numRows:
                self.logWarn(f"Got invalid sell request for row {row} of {self.game.gameConfig.playfield.numRows}.")
                self.set_status(404) # Not found
                return
            if col < 0 or col >= self.game.gameConfig.playfield.numCols:
                self.logWarn(f"Got invalid sell request for col {col} of {self.game.gameConfig.playfield.numCols}.")
                self.set_status(404) # Not found
                return

            try:
                self.game.sellTower(user=user, row=row, col=col)
            except (ValueError, UserInBattleException)  as e:
                self.logInfo("SellHandler error: " + repr(e))
                self.set_status(404) # Not found
                self.write(str(e))
                return

        self.set_status(200) # OK
