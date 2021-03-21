from infinitd_server.battle_computer import BattleCalculationException
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.game import Game, UserInBattleException, UserNotInBattleException
from infinitd_server.handler.base import BaseHandler

class ControlBattleHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    async def post(self, defenderName: str, attackerName: str):
        self.logInfo(f"Got POST request for controlBattle/{defenderName}/{attackerName}")

        with self.getMutableUser(expectedName=defenderName) as defender:
            # Attempt to start a battle
            attacker = self.game.getUserSummaryByName(attackerName)
            try:
                await self.game.startBattle(defender = defender, attacker = attacker,
                        handler = self.__class__.__name__, requestId = self.requestId)
            except (BattleCalculationException) as e:
                self.logError(f"Battle calculation error: {e}", uid=defender.uid)
                self.set_status(409) # Conflict
                self.write(str(e))
                return
            except (ValueError, UserInBattleException) as e:
                self.logInfo("POST error: " + repr(e), uid=defender.uid)
                self.set_status(409) # Conflict
                self.write(str(e))
                return

        self.set_status(201) # Created

    async def delete(self, defenderName: str, attackerName: str):
        self.logInfo(f"Got DELETE request for controlBattle/{attackerName}/{defenderName}")
        # Note: We ignore the attackerName parameter here.

        with self.getMutableUser(expectedName=defenderName) as defender:
            # Attempt to stop the battle
            try:
                await self.game.stopBattle(defender)
            except UserNotInBattleException as e:
                self.logInfo("DELETE error: " + repr(e), uid=defender.uid)
                self.set_status(404) # Not Found
                self.write(str(e))
                return

        self.set_status(204) # No Content
