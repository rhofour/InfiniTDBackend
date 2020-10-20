from infinitdserver.battle import BattleCalculationException
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.game import Game, UserInBattleException, UserNotInBattleException
from infinitdserver.handler.base import BaseHandler

class ControlBattleHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    async def post(self, name: str):
        self.logInfo(f"Got POST request for controlBattle/{name}")

        with self.getMutableUser(expectedName=name) as user:
            # Attempt to start a battle
            try:
                await self.game.startBattle(user=user, handler="ControlBattleHandler", requestId=self.requestId)
            except (BattleCalculationException) as e:
                self.logError(f"Battle calculation error: {e}", uid=user.uid)
                self.set_status(409) # Conflict
                self.write(str(e))
                return
            except (ValueError, UserInBattleException) as e:
                self.logInfo("POST error: " + repr(e), uid=user.uid)
                self.set_status(409) # Conflict
                self.write(str(e))
                return

        self.set_status(201) # Created

    async def delete(self, name: str):
        self.logInfo(f"Got DELETE request for controlBattle/{name}")

        with self.getMutableUser(expectedName=name) as user:
            # Attempt to stop the battle
            try:
                await self.game.stopBattle(name=name)
            except UserNotInBattleException as e:
                self.logInfo("DELETE error: " + repr(e), uid=user.uid)
                self.set_status(404) # Not Found
                self.write(str(e))
                return

        self.set_status(204) # No Content
