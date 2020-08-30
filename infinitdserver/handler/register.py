from infinitdserver.db import Db
from infinitdserver.handler.base import BaseDbHandler

class RegisterHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def post(self, name):
        print("Got request for register/" + name)
        decoded_token = self.verifyAuthentication()
        if (self.db.register(uid=decoded_token["uid"], name=name)):
            self.set_status(201); # CREATED
        else:
            self.set_status(412); # Precondition Failed (assume name is already used)

