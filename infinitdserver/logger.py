import sqlite3
from time import strftime
from typing import Optional

class Logger:
    defaultInstance = None
    printVerbosity: int

    @classmethod
    def getDefault(cls):
        assert cls.defaultInstance is not None
        return cls.defaultInstance

    @classmethod
    def setDefault(cls, newDefault):
        cls.defaultInstance = newDefault

    def __init__(self, db_path: str, printVerbosity : int = 0, debug=False):
        self.printVerbosity = printVerbosity
        self.conn = sqlite3.connect(db_path, isolation_level=None)

        sqlite3.enable_callback_tracebacks(debug)
        self.__create_tables()

    def __del__(self):
        self.conn.close()

    def __create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS logs(
            time TEXT,
            uid TEXT,
            requestId INTEGER,
            handler TEXT,
            msg TEXT,
            verbosity INTEGER
        );""")
        self.conn.commit()

    def error(self, handler: str, requestId: int, msg: str, uid: Optional[str] = None):
        self._log(handler, requestId, msg, verbosity=1, uid=uid)

    def warn(self, handler: str, requestId: int, msg: str, uid: Optional[str] = None):
        self._log(handler, requestId, msg, verbosity=2, uid=uid)

    def info(self, handler: str, requestId: int, msg: str, uid: Optional[str] = None):
        self._log(handler, requestId, msg, verbosity=3, uid=uid)

    def _log(self, handler: str, requestId: int, msg: str, verbosity: int, uid: Optional[str] = None):
        if self.printVerbosity >= verbosity:
            timeStr = strftime("%a %H:%M:%S")
            print(f"{timeStr} {handler} {requestId}: {msg}")
        self.conn.execute(
                "INSERT INTO logs (time, uid, requestId, handler, msg, verbosity) "
                "VALUES (date('now'), :uid, :requestId, :handler, :msg, :verbosity);",
                {
                    "uid": uid if uid else "NULL",
                    "requestId": requestId,
                    "handler": handler,
                    "msg": msg,
                    "verbosity": verbosity,
                })
        self.conn.commit()

class MockLogger(Logger):
    def __init__(self):
        print("Created mock logger")

    def _log(self, handler: str, requestId: int, msg: str, verbosity: int, uid: Optional[str] = None):
        verbosityStr = "???:"
        if verbosity == 1:
            verbosityStr = "ERROR:"
        elif verbosity == 2:
            verbosityStr = "WARN:"
        elif verbosity == 3:
            verbosityStr = "INFO:"
        timeStr = strftime("%a %H:%M:%S")
        print(f"{verbosityStr} {timeStr} {handler} {requestId}: {msg}")

    def __del__(self):
        pass
