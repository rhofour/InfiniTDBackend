import sqlite3

class Db:
    DEFAULT_DB_PATH = "data.db"

    def __init__(self, db_path=None, debug=False):
        if db_path is None:
            db_path = self.DEFAULT_DB_PATH
        self.conn = sqlite3.connect(db_path)
        sqlite3.enable_callback_tracebacks(debug)
        self.__create_tables()

    def __del__(self):
        self.conn.close()
    
    def __create_tables(self):
        users_sql = (
                "CREATE TABLE IF NOT EXISTS users("
                "uid TEXT PRIMARY KEY, "
                "displayName TEXT UNIQUE, "
                "accumulatedGold REAL, "
                "goldPerMinute REAL"
                ");")
        self.conn.execute(users_sql);
        self.conn.commit()

    @staticmethod
    def __extractUserFromRow(row):
        return { "displayName": row["displayName"],
                "accumulatedGold": row["accumulatedGold"],
                "goldPerMinute": row["goldPerMinute"],
                }

    def getUserByUid(self, uid):
        res = self.conn.execute("SELECT displayName, accumulatedGold, goldPerMinute FROM users WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUserByName(self, name):
        res = self.conn.execute("SELECT displayName, accumulatedGold, goldPerMinute FROM users WHERE displayName = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUsers(self):
        res = self.conn.execute("SELECT displayName, accumulatedGold, goldPerMinute FROM users ORDER BY accumulatedGold DESC;")
        res = [ Db.__extractUserFromRow(r) for r in res ]
        return res
