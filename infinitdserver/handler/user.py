from infinitdserver.db import Db
from infinitdserver.handler.base import BaseDbHandler

class UserHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self, username):
        user = self.db.getUserByName(username)
        if user:
            self.write(user.to_dict())
        else:
            self.set_status(404)
