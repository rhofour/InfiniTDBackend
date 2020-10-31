from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class RecordedBattleHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self, attackerName, defenderName):
        print(f"Trying to get battle {attackerName} vs {defenderName}")
        try:
            battle = self.game.getBattle(attackerName, defenderName)
        except ValueError as e:
            self.set_status(404)
            self.write(str(e))
