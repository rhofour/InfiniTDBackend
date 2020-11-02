import cattr

from infinitdserver.battle_computer import BattleCalculationException
from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class RecordedBattleHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self, attackerName, defenderName):
        self.logInfo(f"Trying to get battle {attackerName} vs {defenderName}")
        try:
            battle = self.game.getOrMakeRecordedBattle(attackerName, defenderName,
                    handler = self.__class__.__name__, requestId = self.requestId)
            self.write(cattr.unstructure(battle))
        except (BattleCalculationException) as e:
            self.logError(f"Battle calculation error: {e}")
            self.set_status(409) # Conflict
            self.write(str(e))
            return
        except ValueError as e:
            self.set_status(404)
            self.write(str(e))
