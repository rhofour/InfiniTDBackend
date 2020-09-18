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
        print(f"Got POST request for controlBattle/{name}")

        # Check that the name matches the authorized user
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user.name != name:
            print(f"Got build request for {name} from {user.name}.")
            self.set_status(403) # Forbidden
            return

        self.set_status(201) # CREATED
