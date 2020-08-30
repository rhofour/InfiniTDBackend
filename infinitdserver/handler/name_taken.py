from infinitdserver.db import Db
from infinitdserver.handler.base import BaseDbHandler

class NameTakenHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    # TODO(rofer): Switch to using response headers to send this.
    # 204 for name found, 404 for not found
    def get(self, name):
        print("Got request for isNameTaken/" + name)
        self.write({"isTaken": self.db.nameTaken(name)})
