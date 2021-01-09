import asyncio
from contextlib import contextmanager
import math
import sqlite3
import json
from typing import Optional, List, Callable, Awaitable

from infinitd_server.battle import Battle, BattleResults
from infinitd_server.battle_computer import BattleComputer, BattleCalculationException
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
            "SELECT name, uid, gold, accumulatedGold, goldPerMinute, inBattle, wave, admin, battleground FROM users")
    SELECT_USER_SUMMARY_STATEMENT = (
            "SELECT name, uid, gold, accumulatedGold, goldPerMinute, inBattle, wave, admin FROM users")

    gameConfig: GameConfig
    userQueues: SseQueues
    bgQueues: SseQueues
    battleComputer: BattleComputer
    battleCoordinator: BattleCoordinator
    debug: bool

    def __init__(self, gameConfig: GameConfig, userQueues: SseQueues, bgQueues: SseQueues,
            battleCoordinator: BattleCoordinator, dbPath=None, debug=False):
        self.debug = debug
        if dbPath is None:
            dbPath = self.DEFAULT_DB_PATH
        self.conn = sqlite3.connect(dbPath, isolation_level=None)
        sqlite3.enable_callback_tracebacks(debug)
        # Enable Write-Ahead Logging: https://www.sqlite.org/wal.html
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.__createTables()
        self.gameConfig = gameConfig
        self.userQueues = userQueues
        self.bgQueues = bgQueues
        self.battleComputer = BattleComputer(gameConfig = gameConfig, debug = debug)
        self.battleCoordinator = battleCoordinator
        self.logger = Logger.getDefault()

    def __del__(self):
        self.conn.close()

    def __createTables(self):
        self.conn.execute(
                "CREATE TABLE IF NOT EXISTS users("
                "uid TEXT PRIMARY KEY, "
                "name TEXT UNIQUE, "
                "gold REAL, "
                "accumulatedGold REAL, "
                "goldPerMinute REAL, "
                "inBattle BOOLEAN DEFAULT 0 CHECK (inBattle == 0 || inBattle == 1), "
                "battleground TEXT, "
                "wave TEXT DEFAULT '[]', "
                "admin BOOLEAN DEFAULT 0 CHECK (admin == 0 || admin == 1)"
                ");")
        self.conn.execute(
                "CREATE TABLE IF NOT EXISTS battles("
                "attacking_uid TEXT KEY, "
                "defending_uid TEXT KEY, "
                "events BLOB, "
                "results BLOB"
                ");")
        self.conn.commit()

    @staticmethod
    def __extractUserSummaryFromRow(row) -> FrozenUserSummary:
        return FrozenUserSummary(
                name = row[0],
                uid = row[1],
                gold = row[2],
                accumulatedGold = row[3],
                goldPerMinute = row[4],
                inBattle = row[5] == 1,
                wave = json.loads(row[6]),
                admin = row[7] == 1)

    @staticmethod
    def __extractUserFromRow(row, targetClass=FrozenUser):
        return targetClass(
                name = row[0],
                uid = row[1],
                gold = row[2],
                accumulatedGold = row[3],
                goldPerMinute = row[4],
                inBattle = row[5] == 1,
                wave = json.loads(row[6]),
                admin = row[7] == 1,
                battleground = BattlegroundState.from_json(row[8]))

    def getUserSummaryByName(self, name: str) -> Optional[FrozenUserSummary]:
        res = self.conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserSummaryFromRow(res)
        return None

    def getUserSummaryByUid(self, uid: str) -> Optional[FrozenUserSummary]:
        res = self.conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserSummaryFromRow(res)
        return None

    def getUserByUid(self, uid: str) -> Optional[FrozenUser]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUserByName(self, name: str) -> Optional[FrozenUser]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " WHERE name = ?;", (name, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res)
        return None

    def getUnfrozenUserByUid(self, uid: str) -> Optional[User]:
        res = self.conn.execute(self.SELECT_USER_STATEMENT + " WHERE uid = ?;", (uid, )).fetchone()
        if res:
            return Db.__extractUserFromRow(res, User)
        return None

    def getUsers(self) -> List[FrozenUserSummary]:
        res = self.conn.execute(self.SELECT_USER_SUMMARY_STATEMENT + " ORDER BY accumulatedGold DESC;")
        res = [ Db.__extractUserSummaryFromRow(r) for r in res ]
        return res

    def getBattleground(self, name) -> Optional[BattlegroundState]:
        res = self.conn.execute("SELECT battleground FROM users WHERE name = ?;", (name, )).fetchone()
        if res is None:
            return None
        return BattlegroundState.from_json(res[0])

    def register(self, uid: str, name: str, admin: bool = False):
        """Attempt to register a new user returning whether or not it was successful."""
        assert self.conn.in_transaction is False
        try:
            emptyBattleground = BattlegroundState.empty(self.gameConfig)
            res = self.conn.execute(
                "INSERT INTO users (uid, name, gold, accumulatedGold, goldPerMinute, admin, battleground)"
                " VALUES (:uid, :name, :gold, :gold, :goldPerMinute, :admin, :battleground);",
                {"uid": uid, "name": name, "gold": self.gameConfig.misc.startingGold,
                    "goldPerMinute": self.gameConfig.misc.minGoldPerMinute,
                    "admin": admin, "battleground": emptyBattleground.to_json(),
                })
            self.conn.commit()
        except sqlite3.IntegrityError as err:
            # This is likely because the name was already taken.
            self.logger.warn("DB", -1, f"IntegrityError when registering a new user: {err}", uid=uid)
            return False
        except sqlite3.DatabaseError as err:
            self.logger.warn("DB", -1, f"DatabaseError when registering a new user: {err}", uid=uid)
            return False
        return True

    async def accumulateGold(self):
        """Updates gold and accumulatedGold for every user based on goldPerMinute."""
        with self.transactionContext():
            res = self.conn.execute("SELECT name FROM users WHERE inBattle == 0;")
            namesUpdated = [row[0] for row in res]
            self.conn.execute("""
            UPDATE USERS SET
                accumulatedGold = accumulatedGold + goldPerMinute,
                gold = gold + goldPerMinute
            WHERE inBattle == 0;""");

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
        assert self.conn.in_transaction is False
        self.conn.execute(
                "UPDATE users SET inBattle = :inBattle WHERE name == :name",
                {"inBattle": inBattle, "name": name})
        self.conn.commit()

        if name in self.userQueues:
            user = self.getUserSummaryByName(name)
            await self.userQueues.sendUpdate(name, user)

    async def setBattleground(self, name: str, battleground: BattlegroundState):
        """Directly sets the Battleground for a given user. For test purposes only."""
        self.conn.execute(
                "UPDATE USERS SET battleground = :battleground WHERE name = :name",
                {
                    "battleground": battleground.to_json(),
                    "name": name,
                })
        self.conn.commit()

        await self.__updateBattlegroundListeners(name)

    async def setUserNotInBattle(self, uid: str, name: str):
        "Marks a user as no longer in a battle."
        self.conn.execute("UPDATE users SET inBattle = FALSE where uid = :uid;", { "uid": uid })
        self.conn.commit()
        await self.__updateUserListeners([name])

    def getOrMakeBattle(self, attackingUser: UserSummary, defendingUser: User, handler: str, requestId: int) -> Battle:
        # Ensure this is called from within a transaction or with both users
        # inBattles. Otherwise, it's possible the defender's battleground or
        # the attacker's wave gets changed while the battle is being calculated.
        assert (attackingUser.inBattle and defendingUser.inBattle) or self.conn.in_transaction
        # Check if a battle already exists, if not generate it.
        res = self.conn.execute(
            "SELECT events, results FROM battles "
            "WHERE attacking_uid = :attackingUid AND defending_uid = :defendingUid;",
            { "attackingUid": attackingUser.uid, "defendingUid": defendingUser.uid }
        ).fetchone()
        battleName = f"vs. {attackingUser.name}"
        if res: # Battle exists
            self.logger.info(handler, requestId, f"Found battle: {defendingUser.name} vs {attackingUser.name}")
            events = Battle.decodeEventsFb(res[0])
            results = BattleResults.decodeFb(res[1])
            battle = Battle(events = events, name = battleName, results = results)
            return battle
        else: # Calculate a new battle
            self.logger.info(handler, requestId, f"Calculating new battle: {defendingUser.name} vs {attackingUser.name}")
            battleground = defendingUser.battleground
            if battleground is None: # This should be impossible since we know the user exists.
                raise ValueError(f"Cannot find battleground for {defendingUser.name}")
            battleCalcResults = self.battleComputer.computeBattle(battleground, attackingUser.wave)
            events = Battle.decodeEventsFb(battleCalcResults.fb.EventsAsNumpy().tobytes())
            #eventsFb = battleCalcResults.fb.EventsNestedRoot()
            #events = Battle.decodeEventsFb(eventsFb._tab.Bytes, eventsFb._tab.Pos)
            battle = Battle(events = events, name = battleName,
                    results = battleCalcResults.results)
            self.conn.execute(
                    "INSERT into battles (attacking_uid, defending_uid, events, results) "
                    "VALUES (:attackingUid, :defendingUid, :events, :results);",
                    {
                        "attackingUid": attackingUser.uid, "defendingUid": defendingUser.uid,
                        "events": battleCalcResults.fb.EventsAsNumpy().tobytes(),
                        "results": battleCalcResults.results.encodeFb(),
                    }
            )
            # Don't end a transaction early.
            if not self.conn.in_transaction:
                self.conn.commit()
            return battle

    def clearInBattle(self):
        assert self.conn.in_transaction is False
        self.conn.execute("UPDATE users SET inBattle = FALSE;")
        self.conn.commit()

    def updateUser(self, user: MutableUser, addAwaitable: Callable[[Awaitable[None]], None]):
        "Update a User."
        # This is always called from within a transaction in ModifidableUser.
        assert self.conn.in_transaction is True
        if not user.summaryModified and not user.battlegroundModified:
            return
        # Update all columns except UID.
        if user.battlegroundModified:
            self.conn.execute(
                    "UPDATE users SET "
                    "name = :name, gold = :gold, accumulatedGold = :accumulatedGold, goldPerMinute = :goldPerMinute, "
                    "inBattle = :inBattle, wave = :wave, battleground = :battleground "
                    "where uid = :uid", {
                        "uid": user.uid,
                        "name": user.name,
                        "gold": user.gold,
                        "accumulatedGold": user.accumulatedGold,
                        "goldPerMinute": user.goldPerMinute,
                        "inBattle": user.inBattle,
                        "wave": json.dumps(user.wave),
                        "battleground": user.battleground.to_json(),
                    })

            # Clear any battles where this user was defending now that they have a new battleground.
            self.conn.execute("DELETE from battles WHERE defending_uid = :uid", { "uid": user.uid })
        else: # Skip updating the battleground
            self.conn.execute(
                    "UPDATE users SET "
                    "name = :name, gold = :gold, accumulatedGold = :accumulatedGold, goldPerMinute = :goldPerMinute, "
                    "inBattle = :inBattle, wave = :wave "
                    "where uid = :uid", {
                        "uid": user.uid,
                        "name": user.name,
                        "gold": user.gold,
                        "accumulatedGold": user.accumulatedGold,
                        "goldPerMinute": user.goldPerMinute,
                        "inBattle": user.inBattle,
                        "wave": json.dumps(user.wave),
                    })
        if user.waveModified:
            # Clear any battles where this user was attacking now that they have a different wave.
            self.conn.execute("DELETE from battles WHERE attacking_uid = :uid", { "uid": user.uid })

        # There's no need to commit here as the calling function will do that.

        if user.summaryModified:
            addAwaitable(self.__updateUserListeners([user.name]))
        if user.battlegroundModified:
            addAwaitable(self.__updateBattlegroundListeners(user.name))

    def enterTransaction(self):
        assert self.conn.in_transaction is False
        self.conn.execute("BEGIN IMMEDIATE")

    def leaveTransaction(self):
        assert self.conn.in_transaction is True
        self.conn.commit()

    @contextmanager
    def transactionContext(self):
        self.enterTransaction()
        try:
            yield
        finally:
            self.leaveTransaction()

    def getMutableUserContext(self, uid: str, addAwaitable) -> Optional['MutableUserContext']:
        user = self.getUnfrozenUserByUid(uid)
        if user is None:
            return None
        return MutableUserContext(user, self, addAwaitable)

    def resetBattles(self):
        self.conn.execute("DROP TABLE battles")
        self.conn.commit()
        self.__createTables()
    
    async def resetGameData(self):
        emptyBattleground = BattlegroundState.empty(self.gameConfig)
        self.conn.execute(
            "UPDATE users SET battleground = :emptyBattleground, "
            "gold = :initialGold, accumulatedGold = :initialGold,"
            "goldPerMinute = :goldPerMinute, wave = '[]'",
            {
                 "emptyBattleground": emptyBattleground.to_json(),
                 "initialGold": self.gameConfig.misc.startingGold,
                 "goldPerMinute": self.gameConfig.misc.minGoldPerMinute,
            })
        # self.resetBattles()
        self.conn.commit()

        await self.__updateAllListeners()

class MutableUserContext:
    db: Db
    mutableUser: MutableUser
    addAwaitable: Callable[[Awaitable[None]], None]

    def __init__(self, user: User, db: Db, addAwaitable):
        self.mutableUser = MutableUser(user)
        self.db = db
        self.addAwaitable = addAwaitable

    def __enter__(self):
        self.db.enterTransaction()
        return self.mutableUser

    def __exit__(self, type, value, traceback):
        if self.mutableUser.summaryModified or self.mutableUser.battlegroundModified:
            self.db.updateUser(user = self.mutableUser, addAwaitable = self.addAwaitable)
        self.db.leaveTransaction()
