import asyncio
import math
import sqlite3
import json
from typing import Optional

from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.user import User
from infinitdserver.game_config import GameConfig
from infinitdserver.sse import SseQueues
from infinitdserver.paths import findShortestPaths

class UserInBattleException(Exception):
    pass

class UserHasInsufficientGoldException(Exception):
    pass

class Db:
    DEFAULT_DB_PATH = "data.db"
    SELECT_USER_STATEMENT = (
            "SELECT name, gold, accumulatedGold, goldPerMinute, inBattle, wave FROM users")


    def __init__(self, gameConfig: GameConfig, userQueues: SseQueues, bgQueues: SseQueues, db_path=None, debug=False):
        if db_path is None:
            db_path = self.DEFAULT_DB_PATH
        self.conn = sqlite3.connect(db_path)
        sqlite3.enable_callback_tracebacks(debug)
        # Enable Write-Ahead Logging: https://www.sqlite.org/wal.html
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.__create_tables()
        self.gameConfig = gameConfig
        self.userQueues: SseQueues = userQueues
        self.bgQueues: SseQueues = bgQueues

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
                "battleground TEXT, "
                "wave TEXT DEFAULT '[]'"
                ");")
        self.conn.commit()

    @staticmethod
    def __extractUserFromRow(row) -> User:
        return User(
                name = row[0],
                gold = row[1],
                accumulatedGold = row[2],
                goldPerMinute = row[3],
                inBattle = row[4] == 1,
                wave = json.loads(row[5]))

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
                    {"uid": uid, "name": name, "gold": self.gameConfig.misc.startingGold,
                        "goldPerMinute": self.gameConfig.misc.minGoldPerMinute,
                        "battleground": emptyBattleground.to_json(),
                    })
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

        if namesUpdated:
            await asyncio.wait([self.__updateUser(name) for name in namesUpdated])

    async def __updateUser(self, name):
        if name in self.userQueues:
            user = self.getUserByName(name)
            await self.userQueues.sendUpdate(name, user)

    async def __updateBattleground(self, name):
        if name in self.bgQueues:
            battleground = self.getBattleground(name)
            await self.bgQueues.sendUpdate(name, battleground)

    async def setInBattle(self, name: str, inBattle: bool):
        self.conn.execute(
                "UPDATE users SET inBattle = :inBattle WHERE name == :name",
                {"inBattle": inBattle, "name": name})
        self.conn.commit()

        if name in self.userQueues:
            user = self.getUserByName(name)
            await self.userQueues.sendUpdate(name, user)

    async def setBattleground(self, name: str, battleground: BattlegroundState):
        """Directly sets the Battleground for a given user. For test purposes."""
        self.conn.execute(
                "UPDATE USERS SET battleground = :battleground WHERE name = :name",
                {
                    "battleground": battleground.to_json(),
                    "name": name,
                })
        self.conn.commit()

        await self.__updateBattleground(name)

    async def buildTower(self, name: str, row: int, col: int, towerId: int):
        try:
            towerConfig = self.gameConfig.towers[towerId]
        except IndexError:
            raise ValueError(f"Invalid tower ID {towerId}")

        self.conn.execute("BEGIN IMMEDIATE TRANSACTION")
        user = self.getUserByName(name)
        if user is None:
            raise ValueError(f"{name} is not a registered user.");

        if user.inBattle:
            self.conn.commit()
            raise UserInBattleException()

        if user.gold < towerConfig.cost:
            self.conn.commit()
            raise UserHasInsufficientGoldException(
                    f"{towerConfig.name} costs {towerConfig.cost}, but {name} only has {user.gold} gold.")

        battleground = self.getBattleground(name)
        existingTower = battleground.towers.towers[row][col]
        if existingTower:
            self.conn.commit()
            existingTowerName = self.gameConfig.towers[existingTower.id].name
            raise ValueError(f"{existingTowerName} already exists at row {row}, col {col}.")

        battleground.towers.towers[row][col] = BgTowerState(towerId)

        # Check if there is still a path from start to exit.
        paths = findShortestPaths(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        if not paths:
            self.conn.commit()
            raise ValueError(f"Building at {row}, {col} would block the path.")

        self.conn.execute(
                "UPDATE USERS SET gold = :gold, battleground = :battleground WHERE name = :name",
                {
                    "gold": user.gold - towerConfig.cost,
                    "battleground": battleground.to_json(),
                    "name": name,
                })
        self.conn.commit()

        await asyncio.wait([self.__updateUser(name), self.__updateBattleground(name)])

    async def sellTower(self, name: str, row: int, col: int):
        self.conn.execute("BEGIN IMMEDIATE TRANSACTION")
        user = self.getUserByName(name)
        if user is None:
            self.conn.commit()
            raise ValueError(f"{name} is not a registered user.");

        if user.inBattle:
            self.conn.commit()
            raise UserInBattleException()

        battleground = self.getBattleground(name)
        existingTower: BgTowerState = battleground.towers.towers[row][col]
        if existingTower is None:
            self.conn.commit()
            raise ValueError(f"No tower exists at row {row}, col {col}.")
        try:
            towerConfig = self.gameConfig.towers[existingTower.id]
        except IndexError:
            # This should never happen as long as the game config matches the database.
            raise ValueError(f"Invalid tower ID {towerId}")

        battleground.towers.towers[row][col] = None
        sellAmount = math.floor(towerConfig.cost * self.gameConfig.misc.sellMultiplier)
        self.conn.execute(
                "UPDATE USERS SET gold = :gold, accumulatedGold = :accumulatedGold, battleground = :battleground WHERE name = :name",
                {
                    "gold": user.gold + sellAmount,
                    "accumulatedGold": user.accumulatedGold + sellAmount,
                    "battleground": battleground.to_json(),
                    "name": name,
                })
        self.conn.commit()

        await asyncio.wait([self.__updateUser(name), self.__updateBattleground(name)])

    async def addToWave(self, name: str, monsterId: int):
        try:
            monsterConfig = self.gameConfig.monsters[monsterId]
        except IndexError:
            raise ValueError(f"Invalid monster ID {monsterId}")

        self.conn.execute("BEGIN IMMEDIATE TRANSACTION")
        user = self.getUserByName(name)
        if user is None:
            self.conn.commit()
            raise ValueError(f"{name} is not a registered user.");

        if user.inBattle:
            self.conn.commit()
            raise UserInBattleException()

        existingWave = user.wave
        existingWave.append(monsterId)
        self.conn.execute(
                "UPDATE USERS SET wave = :wave WHERE name = :name",
                {
                    "wave": json.dumps(existingWave),
                    "name": name,
                })
        self.conn.commit()

        await self.__updateUser(name)
