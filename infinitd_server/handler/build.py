import json

import tornado
import tornado.escape

from infinitd_server.game import Game, UserInBattleException, UserHasInsufficientGoldException
from infinitd_server.handler.base import BaseHandler

class BuildHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name: str):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            self.logWarn(f"Error decoding: {self.request.body}")
            self.set_status(400) # Bad request
            return
        self.logInfo(f"Got request for build/{name} with data {data}")
        
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
        try:
            towerIds = data["towerIds"]
        except KeyError:
            self.logWarn(f"Missing towerIds in data: {data}")
            self.set_status(400) # Bad request
            return
        if len(rows) != len(cols) or len(rows) != len(towerIds):
            self.logWarn("rows, cols, and towerIds aren't all the same length: "
                f"{len(rows)}, {len(cols)}, {len(towerIds)}")
            self.set_status(400) # Bad request
            return

        with self.getMutableUser(expectedName=name) as user:
            try:
                self.game.buildTowers(user = user, rows = rows, cols = cols, towerIds = towerIds)
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
