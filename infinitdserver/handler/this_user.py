from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class ThisUserHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self):
        decoded_token = self.verifyAuthentication()
        user = self.game.getUserByUid(decoded_token["uid"])
        if user:
            self.write(user.to_dict())
        else:
            self.set_status(404)
