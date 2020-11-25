import cattr

from infinitd_server.battle_computer import BattleCalculationException
from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class DebugBattleInputHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self, attackerName, defenderName):
        self.logInfo(f"Trying to download battle input for {attackerName} vs {defenderName}")
        attacker = self.game.getUserByName(attackerName)
        if attacker is None:
            self.set_status(404)
            self.write(f"Unknown user: {attackerName}")
            return
        defender = self.game.getUserByName(defenderName)
        if defender is None:
            self.set_status(404)
            self.write(f"Unknown user: {defenderName}")
            return
        data = {
            'battleground': defender.battleground.to_dict(),
            'wave': attacker.wave,
        }
        self.write(data)
