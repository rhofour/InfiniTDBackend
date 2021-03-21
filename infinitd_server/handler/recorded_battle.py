import cattr

from infinitd_server.battle_computer import BattleCalculationException
from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class RecordedBattleHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    async def get(self, attackerName, defenderName):
        self.logInfo(f"Trying to get battle {attackerName} vs {defenderName}")
        try:
            battle = await self.game.getOrMakeRecordedBattle(attackerName, defenderName,
                    handler = self.__class__.__name__, requestId = self.requestId)
            self.logInfo(f"Found battle.")
            self.write(cattr.unstructure(battle))
        except (BattleCalculationException) as e:
            self.logError(f"Battle calculation error: {e}")
            self.set_status(409) # Conflict
            self.write(str(e))
        except ValueError as e:
            self.logError(f"Error: {e}")
            self.set_status(404) # Not found
            self.write(str(e))
