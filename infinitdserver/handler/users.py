from infinitdserver.db import Db
from infinitdserver.handler.base import BaseDbHandler

class UsersHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self):
        print("Got request for /users")
        users = [user.to_dict() for user in self.db.getUsers()]
        data = {'users': users}
        self.write(data)
