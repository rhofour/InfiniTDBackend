from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class RegisterHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def post(self, name):
        self.logInfo("Got request for register/" + name)
        uid = self.verifyAuthentication()
        try:
            self.game.register(uid=uid, name=name)
            self.set_status(201) # CREATED
        except ValueError as e:
            self.set_status(412) # Precondition Failed (assume name is already used)
            self.write(str(e))
