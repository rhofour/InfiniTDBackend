from infinitdserver.battle import BattleCalculationException
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.db import Db, UserInBattleException, UserNotInBattleException, UserHasInsufficientGoldException
from infinitdserver.handler.base import BaseDbHandler

class ControlBattleHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    battleCoordinator: BattleCoordinator

    def initialize(self, db: Db, battleCoordinator: BattleCoordinator):
        super(ControlBattleHandler, self).initialize(db)
        self.db = db
        self.battleCoordinator = BattleCoordinator

    async def post(self, name: str):
        self.logInfo(f"Got POST request for controlBattle/{name}")

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        uid = decoded_token["uid"]
        user = self.db.getUserByUid(uid)
        if user.name != name:
            self.logInfo(f"Got battle start request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        # Attempt to start a battle
        try:
            await self.db.startBattle(name=name, handler="ControlBattleHandler", requestId=self.requestId)
        except (BattleCalculationException) as e:
            self.logError(f"Battle calculation error: {e}", uid=uid)
            self.set_status(409) # Conflict
            self.write(str(e))
            return
        except (ValueError, UserInBattleException, UserHasInsufficientGoldException) as e:
            self.logInfo("POST error: " + repr(e), uid=uid)
            self.set_status(409) # Conflict
            self.write(str(e))
            return

        self.set_status(201) # Created

    async def delete(self, name: str):
        self.logInfo(f"Got DELETE request for controlBattle/{name}")

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        uid = decoded_token["uid"]
        user = self.db.getUserByUid(uid)
        if user.name != name:
            self.logInfo(f"Got battle stop request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        # Attempt to stop the battle
        try:
            await self.db.stopBattle(name=name, handler="ControlBattleHandler", requestId=self.requestId)
        except UserNotInBattleException as e:
            self.logInfo("DELETE error: " + repr(e), uid=uid)
            self.set_status(404) # Not Found
            self.write(str(e))
            return

        self.set_status(204) # No Content
