import attr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class DebugLogsHandler(BaseHandler):
    def get(self):
        logs = [attr.asdict(log) for log in self.logger.getLogs()]
        data = {'logs': logs}
        self.write(data)
