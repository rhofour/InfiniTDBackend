import attr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class UserHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self, username):
        user = self.game.getUserSummaryByName(username)
        if user:
            self.write(attr.asdict(user))
        else:
            self.set_status(404)
