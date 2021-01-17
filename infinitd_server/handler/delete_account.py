import tornado

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class DeleteAccountHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    async def delete(self, name: str):
        decodedToken = self.verifyAuthentication()
        uid = decodedToken["uid"]
        user = self.game.getUserSummaryByUid(uid)
        if name != user.name:
            self.logWarn(f"Got request to delete {name} from incorrect UID {uid}.")
            self.set_status(403) # Forbidden
            raise tornado.web.Finish()

        self.game.deleteAccount(uid)
        self.logInfo("Game reset successfully.")
        self.set_status(204) # No Content