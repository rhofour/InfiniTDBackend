import attr

from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class UsersHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    def get(self):
        users = [attr.asdict(user) for user in self.game.getUserSummaries()]
        data = {'users': users}
        self.write(data)
