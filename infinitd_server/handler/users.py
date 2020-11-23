import attr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class UsersHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self):
        users = [attr.asdict(user) for user in self.game.getUserSummaries()]
        data = {'users': users}
        self.write(data)
