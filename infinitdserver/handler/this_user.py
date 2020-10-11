from infinitdserver.db import Db
from infinitdserver.handler.base import BaseDbHandler

class ThisUserHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self):
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user:
            self.write(user.to_dict())
        else:
            self.write({})
