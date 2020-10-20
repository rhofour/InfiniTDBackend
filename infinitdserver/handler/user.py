from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class UserHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self, username):
        user = self.game.getUserByName(username)
        if user:
            self.write(user.to_dict())
        else:
            self.set_status(404)
