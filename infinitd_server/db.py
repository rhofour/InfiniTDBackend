import asyncio
from contextlib import contextmanager
import math
import sqlite3
import json
from typing import Optional, List, Callable, Awaitable

from infinitd_server.battle import Battle, BattleResults
from infinitd_server.battle_computer import BattleCalculationException
from infinitd_server.battle_computer_pool import BattleComputerPool
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.user import User, UserSummary, FrozenUser, FrozenUserSummary, MutableUser
from infinitd_server.game_config import GameConfig
from infinitd_server.sse import SseQueues
from infinitd_server.paths import pathExists
from infinitd_server.logger import Logger

class Db:
    DEFAULT_DB_PATH = "data/data.db"
    SELECT_USER_STATEMENT = (
            "SELECT name, uid, gold, accumulatedGold, goldPerMinuteSelf, goldPerMinuteOthers, inBattle, wave, admin, battleground FROM users")
    SELECT_USER_SUMMARY_STATEMENT = (
            "SELECT name, uid, gold, accumulatedGold, goldPerMinuteSelf, goldPerMinuteOthers, inBattle, wave, admin FROM users")

    gameConfig: GameConfig
    userQueues: SseQueues
    bgQueues: SseQueues
    battleComputerPool: BattleComputerPool
    battleCoordinator: BattleCoordinator
    debug: bool
    dbPath: str

    def __init__(self, gameConfig: GameConfig, userQueues: SseQueues, bgQueues: SseQueues,
            battleCoordinator: BattleCoordinator, dbPath=None, debug=False):
        self.debug = debug
        self.dbPath = self.DEFAULT_DB_PATH if dbPath is None else dbPath
        sqlite3.enable_callback_tracebacks(debug)
        self.__createTables()
        self.gameConfig = gameConfig
        self.userQueues = userQueues
        self.bgQueues = bgQueues
        self.battleComputerPool = BattleComputerPool(gameConfig = gameConfig, debug = debug)
        self.battleCoordinator = battleCoordinator
        self.logger = Logger.getDefault()

    def __createTables(self):
        with self.makeConnection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users(
                uid TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                gold REAL,
                accumulatedGold REAL,
                goldPerMinuteSelf REAL,
                goldPerMinuteOthers REAL,
                inBattle BOOLEAN DEFAULT 0 CHECK (inBattle == 0 || inBattle == 1),
                battleground TEXT,
                wave TEXT DEFAULT '[]',
                admin BOOLEAN DEFAULT 0 CHECK (admin == 0 || admin == 1)
                );""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS battles(
                attacking_uid TEXT KEY,
                defending_uid TEXT KEY,
                events BLOB,
                results BLOB
                );""")
    
    def makeConnection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.dbPath, isolation_level=None)
        # Enable Write-Ahead Logging: https://www.sqlite.org/wal.html
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    @staticmethod
    def __extractUserSummaryFromRow(row) -> FrozenUserSummary:
        return FrozenUserSummary(
                name = row[0],
                uid = row[1],
                gold = row[2],
                accumulatedGold = row[3],
                goldPerMinuteSelf = row[4],
                goldPerMinuteOthers = row[5],
                inBattle = row[6] == 1,
                wave = json.loads(row[7]),
                admin = row[8] == 1)

    @staticmethod
    def __extractUserFromRow(row, targetClass=FrozenUser):
        return targetClass(
                name = row[0],
                uid = row[1],
                gold = row[2],
                accumulatedGold = row[3],
                goldPerMinuteSelf = row[4],
                goldPerMinuteOthers = row[5],
                inBattle = row[6] == 1,
                wave = json.loads(row[7]),
                admin = row[8] == 1,
                battleground = BattlegroundState.from_json(row[9]))

    def getUserSummaryByName(self, name: str) -> Optional[FrozenUserSummary]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserSummaryFromRow(res)
        return None

    def getUserSummaryByUid(self, uid: str) -> Optional[FrozenUserSummary]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserSummaryFromRow(res)
        return None

    def getUserByUid(self, uid: str) -> Optional[FrozenUser]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUserByName(self, name: str) -> Optional[FrozenUser]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_STATEMENT + " WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUnfrozenUserByUid(self, uid: str) -> Optional[User]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res, User)
        return None

    def getUsers(self) -> List[FrozenUserSummary]:
        with self.makeConnection() as conn:
            res = conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " ORDER BY accumulatedGold DESC;")
        res = [ Db.__extractUserSummaryFromRow(r) for r in res ]
        return res

    def getBattleground(self, name) -> Optional[BattlegroundState]:
        with self.makeConnection() as conn:
            res = conn.execute("SELECT battleground FROM users WHERE name = ?;", (name, )).fetchone()
        if res is None:
            return None
        return BattlegroundState.from_json(res[0])

    def register(self, uid: str, name: str, admin: bool = False):
        """Attempt to register a new user returning whether or not it was successful."""
        try:
            with self.makeConnection() as conn:
                emptyBattleground = BattlegroundState.empty(self.gameConfig)
                conn.execute("""
                    INSERT INTO users
                        (uid, name, gold, accumulatedGold, goldPerMinuteSelf,
                         goldPerMinuteOthers, admin, battleground)
                    VALUES 
                        (:uid, :name, :gold, :gold,
                         :goldPerMinuteSelf, 0, :admin, :battleground);""",
                    {"uid": uid, "name": name, "gold": self.gameConfig.misc.startingGold,
                        "goldPerMinuteSelf": self.gameConfig.misc.minGoldPerMinute,
                        "admin": admin, "battleground": emptyBattleground.to_json(),
                    })
        except sqlite3.IntegrityError as err:
            # This is likely because the name was already taken.
            self.logger.warn("DB", -1, f"IntegrityError when registering a new user: {err}", uid=uid)
            raise ValueError(f"Username {name} is already taken.")
        except sqlite3.DatabaseError as err:
            self.logger.warn("DB", -1, f"DatabaseError when registering a new user: {err}", uid=uid)
            raise err

    async def accumulateGold(self):
        """Updates gold and accumulatedGold for every user based on goldPerMinute."""
        with self.makeConnection() as conn:
            res = conn.execute("SELECT name FROM users WHERE inBattle == 0;")
            namesUpdated = [row[0] for row in res]
            conn.execute("""
            UPDATE users SET
                accumulatedGold = accumulatedGold + goldPerMinuteSelf + goldPerMinuteOthers,
                gold = gold + goldPerMinuteSelf + goldPerMinuteOthers
            WHERE inBattle == 0;""")

        await self.__updateUserListeners(namesUpdated)

    async def __updateBattlegroundListeners(self, name):
        if name in self.bgQueues:
            battleground = self.getBattleground(name)
            await self.bgQueues.sendUpdate(name, battleground)

    async def __updateAllListeners(self):
        updateCalls = []
        for name in self.userQueues.keys():
            user = self.getUserSummaryByName(name)
            updateCalls.append(self.userQueues.sendUpdate(name, user))
        for name in self.bgQueues.keys():
            battleground = self.getBattleground(name)
            updateCalls.append(self.bgQueues.sendUpdate(name, battleground))
        if updateCalls:
            await asyncio.wait(updateCalls)

    async def __updateUserListeners(self, names: List[str]):
        updateCalls = []
        for name in names:
            if name in self.userQueues:
                user = self.getUserSummaryByName(name)
                updateCalls.append(self.userQueues.sendUpdate(name, user))
        if updateCalls:
            await asyncio.wait(updateCalls)


    async def setInBattle(self, name: str, inBattle: bool):
        with self.makeConnection() as conn:
            conn.execute(
                "UPDATE users SET inBattle = :inBattle WHERE name == :name;",
                {"inBattle": inBattle, "name": name})

        if name in self.userQueues:
            user = self.getUserSummaryByName(name)
            await self.userQueues.sendUpdate(name, user)

    async def setBattleground(self, name: str, battleground: BattlegroundState):
        """Directly sets the Battleground for a given user. For test purposes only."""
        with self.makeConnection() as conn:
            conn.execute(
                "UPDATE USERS SET battleground = :battleground WHERE name = :name",
                {
                    "battleground": battleground.to_json(),
                    "name": name,
                })

        await self.__updateBattlegroundListeners(name)

    async def setUserNotInBattle(self, uid: str, name: str):
        "Marks a user as no longer in a battle."
        with self.makeConnection() as conn:
            conn.execute("UPDATE users SET inBattle = FALSE where uid = :uid;", { "uid": uid })
        await self.__updateUserListeners([name])

    def getBattle(self, attackingUser: FrozenUserSummary, defendingUser: FrozenUserSummary, conn: sqlite3.Connection) -> Optional[Battle]:
        res = conn.execute(
            "SELECT events, results FROM battles "
            "WHERE attacking_uid = :attackingUid AND defending_uid = :defendingUid;",
            { "attackingUid": attackingUser.uid, "defendingUid": defendingUser.uid }
        ).fetchone()

        if res is None:
            return None

        battleName = f"vs. {attackingUser.name}"
        events = Battle.decodeEventsFb(res[0])
        results = BattleResults.decodeFb(res[1])
        battle = Battle(events = events, name = battleName, results = results)
        return battle

    async def getOrMakeBattle(self, attacker: UserSummary, defender: User, handler: str, requestId: int) -> Battle:
        """Returns a battle between attacker and defender, generating it if necessary"""

        with self.makeConnection() as conn:
            existingBattle = self.getBattle(attacker, defender, conn)
            if existingBattle: # Battle exists
                self.logger.info(handler, requestId, f"Found battle: {existingBattle.name}")
                return existingBattle

        # Calculate a new battle
        self.logger.info(handler, requestId, f"Calculating new battle: {defender.name} vs {attacker.name}")
        if defender.battleground is None: # This should be impossible since we know the user exists.
            raise ValueError(f"Cannot find battleground for {defender.name}")
        battleCalcResults = await self.battleComputerPool.computeBattle(defender.battleground, attacker.wave)
        events = Battle.fbToEvents(battleCalcResults.fb.EventsNestedRoot())
        battleName = f"vs. {attacker.name}"
        battle = Battle(events = events, name = battleName, results = battleCalcResults.results)
        # Check if attacker wave or defender battleground changed since the start.
        with self.makeConnection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            safeToWrite = True
            latestAttacker = self.getUserSummaryByUid(attacker.uid)
            if latestAttacker.wave != attacker.wave:
                safeToWrite = False
                self.logger.info(handler, requestId, f"Attacker {attacker.name}'s wave has changed. Recalculating.")
            if safeToWrite:
                latestDefender = self.getUserByUid(defender.uid)
                if latestDefender.battleground != defender.battleground:
                    safeToWrite = False
                    self.logger.info(handler, requestId, f"Defender {defender.name}'s battleground has changed. Recalculating.")
            if safeToWrite:
                # We can safely write the battle.
                conn.execute(
                    "INSERT into battles (attacking_uid, defending_uid, events, results) "
                    "VALUES (:attackingUid, :defendingUid, :events, :results);",
                    {
                        "attackingUid": attacker.uid, "defendingUid": defender.uid,
                        "events": battleCalcResults.fb.EventsAsNumpy().tobytes(),
                        "results": battleCalcResults.results.encodeFb(),
                    }
                )
                return battle

        # If we've gotten here it means either the attacking wave or defending battleground changed.
        # Retry with the latest attacker and defender information.
        return self.getOrMakeBattle(attacker=latestAttacker, defender=latestDefender,
            handler=handler, requestId=requestId)

    def clearInBattle(self):
        with self.makeConnection() as conn:
            conn.execute("UPDATE users SET inBattle = FALSE;")
            conn.commit()

    def updateUser(self, user: MutableUser, addAwaitable: Callable[[Awaitable[None]], None]):
        "Update a User."
        # This is always called from within a transaction in MutableUser.
        assert user.conn.in_transaction is True
        if not user.summaryModified and not user.battlegroundModified:
            return
        # Update all columns except UID.
        if user.battlegroundModified:
            user.conn.execute("""
                UPDATE users SET
                    name = :name, gold = :gold, accumulatedGold = :accumulatedGold,
                    goldPerMinuteSelf = :goldPerMinuteSelf, goldPerMinuteOthers = :goldPerMinuteOthers, inBattle = :inBattle,
                    wave = :wave, battleground = :battleground
                WHERE uid = :uid""", {
                    "uid": user.uid,
                    "name": user.name,
                    "gold": user.gold,
                    "accumulatedGold": user.accumulatedGold,
                    "goldPerMinuteSelf": user.goldPerMinuteSelf,
                    "goldPerMinuteOthers": user.goldPerMinuteOthers,
                    "inBattle": user.inBattle,
                    "wave": json.dumps(user.wave),
                    "battleground": user.battleground.to_json(),
                })

            # Clear any battles where this user was defending now that they have a new battleground.
            user.conn.execute("DELETE from battles WHERE defending_uid = :uid", { "uid": user.uid })
        else: # Skip updating the battleground
            user.conn.execute("""
                UPDATE users SET
                    name = :name, gold = :gold, accumulatedGold = :accumulatedGold,
                    goldPerMinuteSelf = :goldPerMinuteSelf, goldPerMinuteOthers = :goldPerMinuteOthers, inBattle = :inBattle,
                    wave = :wave
                WHERE uid = :uid""", {
                    "uid": user.uid,
                    "name": user.name,
                    "gold": user.gold,
                    "accumulatedGold": user.accumulatedGold,
                    "goldPerMinuteSelf": user.goldPerMinuteSelf,
                    "goldPerMinuteOthers": user.goldPerMinuteOthers,
                    "inBattle": user.inBattle,
                    "wave": json.dumps(user.wave),
                })
        if user.waveModified:
            # Clear any battles where this user was attacking now that they have a different wave.
            user.conn.execute("DELETE from battles WHERE attacking_uid = :uid", { "uid": user.uid })

        # There's no need to commit here as the calling function will do that.

        if user.summaryModified:
            addAwaitable(self.__updateUserListeners([user.name]))
        if user.battlegroundModified:
            addAwaitable(self.__updateBattlegroundListeners(user.name))

    def enterTransaction(self, conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
        if conn is None:
            conn = self.makeConnection()
        conn.execute("BEGIN IMMEDIATE")
        return conn

    def leaveTransaction(self, conn):
        assert conn.in_transaction is True
        conn.commit()

    def getMutableUserContext(self, uid: str, addAwaitable) -> Optional['MutableUserContext']:
        user = self.getUnfrozenUserByUid(uid)
        if user is None:
            return None
        return MutableUserContext(user, self, addAwaitable)

    def resetBattles(self):
        with self.makeConnection() as conn:
            conn.execute("DROP TABLE battles")

        self.__createTables()
    
    async def resetGameData(self):
        emptyBattleground = BattlegroundState.empty(self.gameConfig)
        with self.makeConnection() as conn:
            conn.execute("""
                UPDATE users
                SET 
                    battleground = :emptyBattleground, gold = :initialGold, accumulatedGold = :initialGold,
                    goldPerMinuteSelf = :goldPerMinuteSelf, goldPerMinuteOthers = 0, wave = '[]',
                    inBattle = 0""",
                {
                    "emptyBattleground": emptyBattleground.to_json(),
                    "initialGold": self.gameConfig.misc.startingGold,
                    "goldPerMinuteSelf": self.gameConfig.misc.minGoldPerMinute,
                })
            self.resetBattles()

        await self.__updateAllListeners()
    
    def deleteAccount(self, uid: str):
        with self.makeConnection() as conn:
            print(f"uid: {uid}")
            conn.execute(
                "DELETE FROM users WHERE uid = :uid",
                { "uid": uid })
            conn.execute(
                "DELETE FROM battles WHERE attacking_uid = :uid OR defending_uid = :uid",
                { "uid": uid })

class MutableUserContext:
    db: Db
    mutableUser: MutableUser
    addAwaitable: Callable[[Awaitable[None]], None]

    def __init__(self, user: User, db: Db, addAwaitable):
        self.db = db
        self.mutableUser = MutableUser(user, self.db.makeConnection())
        self.addAwaitable = addAwaitable

    def __enter__(self):
        self.db.enterTransaction(self.mutableUser.conn)
        return self.mutableUser

    def __exit__(self, type, value, traceback):
        if self.mutableUser.summaryModified or self.mutableUser.battlegroundModified:
            self.db.updateUser(user = self.mutableUser, addAwaitable = self.addAwaitable)
        self.db.leaveTransaction(self.mutableUser.conn)
