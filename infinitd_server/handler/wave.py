import json

import tornado
import tornado.escape

from infinitd_server.game import Game, UserInBattleException, UserHasInsufficientGoldException
from infinitd_server.game_config import GameConfig
from infinitd_server.handler.base import BaseHandler

class WaveHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name: str):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            self.logError(f"Error decoding POST with: {self.request.body}")
            self.set_status(400)
            return
        self.logInfo(f"Got POST request for wave/{name} with data {data}")
        try:
            monsterId = data["monsterId"]
        except KeyError:
            self.logWarn(f"Missing monsterId in data: {data}")
            self.set_status(400)
            return

        with self.getMutableUser(expectedName=name) as user:
            try:
                self.game.addToWave(user, monsterId=monsterId)
            except ValueError as e:
                self.logWarn("Wave ValueError: " + repr(e), uid=user.uid)
                self.set_status(400) # Bad request
                self.write(str(e))
                return
            except UserInBattleException  as e:
                self.logWarn("Wave UserInBattleException: " + repr(e), uid=user.uid)
                self.set_status(409) # Conflict
                self.write(str(e))
                return

        self.set_status(201) # OK

    def delete(self, name: str):
        self.logInfo(f"Got DELETE request for wave/{name}")

        with self.getMutableUser(expectedName=name) as user:
            try:
                self.game.clearWave(user)
            except (ValueError, UserInBattleException)  as e:
                self.logWarn("Wave DELETE error: " + repr(e), uid=user.uid)
                self.set_status(404) # Not found
                self.write(str(e))
                return

        self.set_status(200) # OK
