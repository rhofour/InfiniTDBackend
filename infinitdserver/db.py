import sqlite3

class Db:
    DEFAULT_DB_PATH = "data.db"
    STARTING_GOLD = 100.0

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
                "name TEXT UNIQUE, "
                "accumulatedGold REAL, "
                "goldPerMinute REAL"
                ");")
        self.conn.execute(users_sql);
        self.conn.commit()

    @staticmethod
    def __extractUserFromRow(row):
        return { "name": row[0],
                "accumulatedGold": row[1],
                "goldPerMinute": row[2],
                }

    def getUserByUid(self, uid):
        res = self.conn.execute("SELECT name, accumulatedGold, goldPerMinute FROM users WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUserByName(self, name):
        res = self.conn.execute("SELECT name, accumulatedGold, goldPerMinute FROM users WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUsers(self):
        res = self.conn.execute("SELECT name, accumulatedGold, goldPerMinute FROM users ORDER BY accumulatedGold DESC;")
        res = [ Db.__extractUserFromRow(r) for r in res ]
        return res

    def nameTaken(self, name):
        res = self.conn.execute("SELECT name FROM users WHERE name = ?;", (name, )).fetchone()
        if res is None:
            return False
        return True

    def register(self, uid=None, name=None):
        """Attempt to register a new user returning whether or not it was successful."""
        if not uid:
            raise ValueError("Register requires a UID.")
        if not name:
            raise ValueError("Register requires a name.")
        try:
            res = self.conn.execute("INSERT INTO users (uid, name, accumulatedGold, goldPerMinute) VALUES (:uid, :name, :gold, 0.0);",
                    {"uid": uid, "name": name, "gold": self.STARTING_GOLD})
            self.conn.commit()
        except sqlite3.IntegrityError as err:
            # This is likely because the name was already taken. 
            print("IntegrityError when registering a new user: ", err)
            return False
        except sqlite3.DatabaseError as err:
            print("DatabaseError when registering a new user: ", err)
            return False
        return True

