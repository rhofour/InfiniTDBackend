import tornado

from infinitd_server.game import Game, UserNotAdminException
from infinitd_server.handler.base import BaseHandler

class ResetGameHandler(BaseHandler):
    game: Game # See https://github.com/google/pytype/issues/652

    async def post(self):
        decodedToken = self.verifyAuthentication()
        uid = decodedToken["uid"]
        try:
            await self.game.resetGameData(uid)
        except UserNotAdminException:
            self.logWarn("Game reset attempted by non-admin user.", uid=uid)
            self.set_status(403) # Forbidden
            raise tornado.web.Finish()
        self.logInfo("Game reset successfully.", uid=uid)