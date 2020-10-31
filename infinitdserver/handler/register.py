from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class RegisterHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name):
        self.logInfo("Got request for register/" + name)
        decoded_token = self.verifyAuthentication()
        if (self.game.register(uid=decoded_token["uid"], name=name)):
            self.set_status(201); # CREATED
        else:
            self.set_status(412); # Precondition Failed (assume name is already used)
