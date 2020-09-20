import json

import tornado
import tornado.escape

from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.game_config import GameConfig
from infinitdserver.handler.base import BaseDbHandler

class WaveHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    gameConfig: GameConfig

    def initialize(self, db, gameConfig):
        super(WaveHandler, self).initialize(db)
        self.gameConfig = gameConfig

    async def post(self, name: str):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            print(f"WaveHandler: Error decoding POST with: {self.request.body}")
            self.set_status(400)
            return
        print(f"Got POST request for wave/{name} with data {data}")
        try:
            monsterId = data["monsterId"]
        except KeyError:
            self.set_status(400)
            return
        if monsterId < 0 or monsterId >= len(self.gameConfig.monsters):
            self.set_status(400)
            return

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got wave POST request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        try:
            await self.db.addToWave(name=name, monsterId=monsterId)
        except (ValueError, UserInBattleException)  as e:
            print("Wave POST error: " + repr(e))
            self.set_status(409) # Conflict
            self.write(str(e))
            return

        self.set_status(201) # OK

    async def delete(self, name: str):
        print(f"Got DELETE request for wave/{name}")

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got wave DELETE request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        try:
            await self.db.clearWave(name=name)
        except (ValueError, UserInBattleException)  as e:
            print("Wave DELETE error: " + repr(e))
            self.set_status(404) # Not found
            self.write(str(e))
            return

        self.set_status(200) # OK
