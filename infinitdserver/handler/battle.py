from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.db import Db, UserInBattleException, UserHasInsufficientGoldException
from infinitdserver.handler.base import BaseDbHandler

class BattleHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652
    battleCoordinator: BattleCoordinator

    def initialize(self, db: Db, battleCoordinator: BattleCoordinator):
        super(BattleHandler, self).initialize(db)
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
            await self.db.startBattle(name=name, handler="BattleHandler", requestId=self.requestId)
        except (ValueError, UserInBattleException, UserHasInsufficientGoldException) as e:
            self.logInfo("BattleHandler POST error: " + repr(e), uid=uid)
            self.set_status(409) # Conflict
            self.write(str(e))
            return

        self.set_status(201) # CREATED
