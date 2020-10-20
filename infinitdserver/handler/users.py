from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class UsersHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self):
        users = [user.to_dict() for user in self.game.getUsers()]
        data = {'users': users}
        self.write(data)
