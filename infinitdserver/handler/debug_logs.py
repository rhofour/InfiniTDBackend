import attr

from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class DebugLogsHandler(BaseHandler):
    def get(self):
        logs = [attr.asdict(log) for log in self.logger.getLogs()]
        data = {'logs': logs}
        self.write(data)
