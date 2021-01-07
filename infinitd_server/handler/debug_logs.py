import attr

from infinitd_server.game import Game
from infinitd_server.handler.base import BaseHandler

class DebugLogsHandler(BaseHandler):
    def get(self):
        minVerbosity = int(self.get_argument("minVerbosity", "0"))
        if minVerbosity < 0 or minVerbosity > 3:
            raise ValueError(
                f"Got invalid value ({minVerbosity}) for min verbosity."
                "It must be between 0 and 3 inclusive.")
        maxVerbosity = int(self.get_argument("maxVerbosity", "3"))
        if maxVerbosity < 0 or maxVerbosity > 3:
            raise ValueError(
                f"Got invalid value ({maxVerbosity}) for max verbosity."
                "It must be between 0 and 3 inclusive.")
        logs = self.logger.getLogs(minVerbosity=minVerbosity, maxVerbosity=maxVerbosity)
        data = {'logs': [attr.asdict(log) for log in logs]}
        self.write(data)
