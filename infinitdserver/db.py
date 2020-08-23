import sqlite3
import json
from typing import Optional

from infinitdserver.battleground_state import BattlegroundState, BgTowersState
from infinitdserver.user import User
from infinitdserver.game_config import GameConfig
from infinitdserver.sse import SseQueues

class Db:
    DEFAULT_DB_PATH = "data.db"
    STARTING_GOLD = 100
    STARTING_GOLD_PER_MINUTE = 1
    SELECT_USER_STATEMENT = (
            "SELECT name, gold, accumulatedGold, goldPerMinute, inBattle FROM users")


    def __init__(self, gameConfig: GameConfig, userQueues: SseQueues, db_path=None, debug=False):
        if db_path is None:
            db_path = self.DEFAULT_DB_PATH
        self.conn = sqlite3.connect(db_path)
        sqlite3.enable_callback_tracebacks(debug)
        self.__create_tables()
        self.gameConfig = gameConfig
        self.userQueues: SseQueues = userQueues

    def __del__(self):
        self.conn.close()

    def __create_tables(self):
        self.conn.execute(
                "CREATE TABLE IF NOT EXISTS users("
                "uid TEXT PRIMARY KEY, "
                "name TEXT UNIQUE, "
                "gold REAL, "
                "accumulatedGold REAL, "
                "goldPerMinute REAL, "
                "inBattle BOOLEAN DEFAULT 0 CHECK (inBattle == 0 || inBattle == 1), "
                "battleground TEXT"
                ");")
        self.conn.commit()

    @staticmethod
    def __extractUserFromRow(row) -> User:
        return User(
                name = row[0],
                gold = row[1],
                accumulatedGold = row[2],
                goldPerMinute = row[3],
                inBattle = row[4] == 1)

    def getUserByUid(self, uid) -> Optional[User]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUserByName(self, name) -> Optional[User]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUsers(self) -> Optional[User]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " ORDER BY accumulatedGold DESC;")
        res = [ Db.__extractUserFromRow(r) for r in res ]
        return res

    def getBattleground(self, name) -> Optional[BattlegroundState]:
        res = self.conn.execute("SELECT battleground FROM users WHERE name = ?;", (name, )).fetchone()
        if res is None:
            return None
        return BattlegroundState.from_json(res[0])

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
            emptyBattleground = BattlegroundState.empty(self.gameConfig)
            res = self.conn.execute("INSERT INTO users (uid, name, gold, accumulatedGold, goldPerMinute, battleground)"
                    " VALUES (:uid, :name, :gold, :gold, :goldPerMinute, :battleground);",
                    {"uid": uid, "name": name, "gold": self.STARTING_GOLD, "goldPerMinute": self.STARTING_GOLD_PER_MINUTE,
                        "battleground": emptyBattleground.to_json()})
            self.conn.commit()
        except sqlite3.IntegrityError as err:
            # This is likely because the name was already taken. 
            print("IntegrityError when registering a new user: ", err)
            return False
        except sqlite3.DatabaseError as err:
            print("DatabaseError when registering a new user: ", err)
            return False
        return True

    async def accumulateGold(self):
        """Updates gold and accumulatedGold for every user based on goldPerMinute."""
        res = self.conn.execute("SELECT name FROM users WHERE inBattle == 0;")
        namesUpdated = [row[0] for row in res]
        self.conn.execute("""
        UPDATE USERS SET
            accumulatedGold = accumulatedGold + goldPerMinute,
            gold = gold + goldPerMinute
        WHERE inBattle == 0;""");
        self.conn.commit()

        for name in namesUpdated:
            if name in self.userQueues:
                user = self.getUserByName(name)
                await self.userQueues.sendUpdate(name, user)

    async def setInBattle(self, name: str, inBattle: bool):
        self.conn.execute(
                "UPDATE users SET inBattle = :inBattle WHERE name == :name",
                {"inBattle": inBattle, "name": name})
        self.conn.commit()

        if name in self.userQueues:
            user = self.getUserByName(name)
            await self.userQueues.sendUpdate(name, user)
