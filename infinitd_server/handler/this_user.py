import attr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class ThisUserHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self):
        uid = self.verifyAuthentication()
        user = self.game.getUserSummaryByUid(uid)
        if user:
            self.write(attr.asdict(user))
        else:
            self.set_status(404)
