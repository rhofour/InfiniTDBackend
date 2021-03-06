import asyncio
import copy
from typing import List, Optional, Awaitable, Callable, Dict
import math

import firebase_admin.auth

from infinitd_server.battle import Battle, BattleResults
from infinitd_server.battle_computer import BattleCalculationException
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.battle_coordinator import BattleCoordinator
from infinitd_server.db import Db, MutableUserContext
from infinitd_server.game_config import GameConfig, ConfigId
from infinitd_server.logger import Logger
from infinitd_server.sse import SseQueues
from infinitd_server.user import User, FrozenUser, FrozenUserSummary, MutableUser
from infinitd_server.paths import pathExists
from infinitd_server.rivals import Rivals

class UserInBattleException(Exception):
    pass

class UserNotInBattleException(Exception):
    pass

class UserHasInsufficientGoldException(Exception):
    pass

class UserNotAdminException(Exception):
    pass

class UserMatchingError(Exception):
    def __init__(self, actualName: str, expectedName: str):
        self.actualName = actualName
        self.expectedName = expectedName

    def __str__(self):
        return f"Expected username {self.expectedName}, got username {self.actualName}."

GOLD_EPSILON = 0.09 # Handle floating point errors by being slightly lenient on the client

class Game:

    gameConfig: GameConfig
    queues: Dict[str, SseQueues]
    _battleCoordinator: BattleCoordinator
    _db: Db

    def __init__(self, gameConfig: GameConfig, debug: bool = False, dbPath = None):
        self.gameConfig = gameConfig
        self.logger = Logger.getDefault()

        # Make queues for streams
        self.queues = {}
        for datatype in ["battle", "battleground", "user", "rivals", "battleGpm"]:
            self.queues[datatype] = SseQueues()

        self.battleCoordinator = BattleCoordinator(self.queues["battle"])
        self._db = Db(
                gameConfig = self.gameConfig,
                userQueues = self.queues["user"],
                bgQueues = self.queues["battleground"],
                rivalsQueues = self.queues["rivals"],
                battleGpmQueues = self.queues["battleGpm"],
                battleCoordinator = self.battleCoordinator,
                debug=debug,
                dbPath = dbPath)

    def getUserSummaries(self) -> List[FrozenUserSummary]:
        return self._db.getUsers()

    def getUserSummaryByName(self, name: str) -> Optional[FrozenUserSummary]:
        return self._db.getUserSummaryByName(name)

    def getUserSummaryByUid(self, uid: str) -> Optional[FrozenUserSummary]:
        return self._db.getUserSummaryByUid(uid)

    def getUserByName(self, name: str) -> Optional[User]:
        return self._db.getUserByName(name)

    def getUserByUid(self, uid: str) -> Optional[User]:
        return self._db.getUserByUid(uid)

    def getMutableUserContext(self, uid: str, expectedName: str) -> MutableUserContext:
        mutableUserContext = self._db.getMutableUserContext(uid)
        if mutableUserContext is None:
            raise ValueError(f"User with UID = {uid} not found.")
        # Compare against expected name
        if mutableUserContext.mutableUser.name != expectedName:
            raise UserMatchingError(actualName = mutableUserContext.mutableUser.name, expectedName = expectedName)
        # Build mutable user context
        return mutableUserContext

    def register(self, uid: str, name: str, admin: bool = False) -> bool:
        # Require name to be between 2-15 characters
        if len(name) < 2 or len(name) > 15:
            raise ValueError(f"Name must have between 2-15 character. {name} contains {len(name)}.")
        self._db.register(uid=uid, name=name, admin=admin)

    def getBattleground(self, name: str) -> BattlegroundState:
        return self._db.getBattleground(name)

    def buildTowers(self, user: MutableUser, rows: int, cols: int, towerIds: int):
        if user.inBattle:
            raise UserInBattleException()

        totalCost = 0.0
        newBattleground = copy.deepcopy(user.battleground)
        n = len(rows)
        for i in range(n):
            # Assumes rows, cols, and towerIds are all the same length.
            row = rows[i]
            if row < 0 or row >= self.gameConfig.playfield.numRows:
                raise ValueError(f"Got invalid row value {row}.")
            col = cols[i]
            if col < 0 or col >= self.gameConfig.playfield.numCols:
                raise ValueError(f"Got invalid row value {col}.")
            towerId = towerIds[i]
            try:
                towerConfig = self.gameConfig.towers.get(towerId)
            except KeyError:
                raise ValueError(f"Got invalid tower ID {towerId}.")
            totalCost += towerConfig.cost
            # Be sure to check newBattleground to catch duplicate towers in a request
            existingTower = newBattleground.towers.towers[row][col]
            if existingTower:
                existingTowerName = self.gameConfig.towers[existingTower.id].name
                raise ValueError(f"{existingTowerName} already exists at row {row}, col {col}.")
            newBattleground.towers.towers[row][col] = BgTowerState(towerId)

        if user.gold + GOLD_EPSILON < totalCost:
            raise UserHasInsufficientGoldException(
                    f"{n} towers cost {totalCost}, but {user.name} only has {user.gold} gold.")

        # Check if there is still a path from start to exit.
        blocked = not pathExists(newBattleground, self.gameConfig.playfield.monsterEnter, self.gameConfig.playfield.monsterExit)
        if blocked:
            raise ValueError(f"Building at {row}, {col} would block the path.")

        # Actually change the user
        user.gold -= totalCost
        user.battleground = newBattleground

    def sellTowers(self, user: MutableUser, rows: List[int], cols: List[int]):
        if user.inBattle:
            raise UserInBattleException()

        totalAmount = 0.0
        newBattleground = copy.deepcopy(user.battleground)
        n = len(rows)
        for i in range(n):
            # Assumes rows, cols, and towerIds are all the same length.
            row = rows[i]
            if row < 0 or row >= self.gameConfig.playfield.numRows:
                raise ValueError(f"Got invalid row value {row}.")
            col = cols[i]
            if col < 0 or col >= self.gameConfig.playfield.numCols:
                raise ValueError(f"Got invalid row value {col}.")
            
            tower = user.battleground.towers.towers[row][col]
            if tower is None:
                raise ValueError(f"No tower exists at row {row}, col {col}.")
            try:
                towerConfig = self.gameConfig.towers.get(tower.id)
            except KeyError:
                raise ValueError(f"Found invalid tower ID {towerId} at row {col}, col {col}.")
            totalAmount += math.floor(towerConfig.cost * self.gameConfig.misc.sellMultiplier)
            newBattleground.towers.towers[row][col] = None
        
        # Actually modify the user
        user.gold += totalAmount
        user.accumulatedGold += totalAmount
        user.battleground = newBattleground

    def setWave(self, user: MutableUser, monsters: List[ConfigId]):
        if user.inBattle:
            raise UserInBattleException()

        if len(monsters) > 500:
            raise ValueError(f"Wave contains {len(monsters)} which is greater than the maximum of 500.")

        for monsterId in monsters:
            # Check every monster ID is known.
            if monsterId not in self.gameConfig.monsters:
                raise ValueError(f"Invalid monster ID {monsterId}")

        user.wave = monsters

    def clearWave(self, user: MutableUser):
        if user.inBattle:
            raise UserInBattleException()

        user.wave = []

    def joinBattle(self, name: str):
        return self.battleCoordinator.getBattle(name).join()

    async def startBattle(self, defender: MutableUser, attacker: FrozenUserSummary,
            handler: str, requestId: int):
        if defender.inBattle:
            raise UserInBattleException()

        defender.inBattle = True
        # Manually update the user and end the transaction while the battle is
        # calculated. Since the user is marked as in battle none of their data
        # can change even outside of the transaction.
        self._db.updateUser(defender)
        self._db.leaveTransaction(defender.conn)

        try:
            battle = await self._db.getOrMakeBattle(
                attacker = attacker, defender = defender.user, handler=handler, requestId=requestId)
        except BattleCalculationException as e:
            self._db.enterTransaction(defender.conn)
            # Prevent a user from getting stuck in a battle
            defender.inBattle = False
            raise e

        # We need this because the user context is expecting to be in a
        # transaction at the end.
        self._db.enterTransaction(defender.conn)

        def setUserNotInBattleCallback():
            self._db.setUserNotInBattle(uid=defender.uid, name=defender.name)

        def updateWithBattleResults(results: BattleResults):
            userContext = self._db.getMutableUserContext(defender.uid)
            if userContext is None:
                raise ValueError(f"UID {defender.uid} doesn't correspond to a user.")
            with userContext as futureUser:
                # Ensure user is in a battle when this is called.
                if not futureUser.inBattle:
                    raise ValueError(f"User {defender.name} isn't in a battle.")
                if results.timeSecs <= 0:
                    raise ValueError(f"Battle results has non-positive time: {results.timeSecs}.")

                if defender.uid == attacker.uid:
                    futureUser.addGold(results.reward)
                    futureUser.goldPerMinuteSelf = results.goldPerMinute
                else:
                    futureUser.addGold(results.reward * self.gameConfig.misc.rivalMultiplier)

        self.battleCoordinator.startBattle(
                battleId = defender.name,
                battle= battle,
                resultsCallback = updateWithBattleResults,
                endCallback = setUserNotInBattleCallback,
                handler = handler, requestId = requestId)

    def getBattle(self, attacker: FrozenUserSummary, defender: FrozenUserSummary) -> Optional[Battle]:
        """Attempts to get a battle if it exists."""
        with self._db.makeConnection() as conn:
            return self._db.getBattle(attacker, defender, conn)

    async def getOrMakeRecordedBattle(self, attackerName: str, defenderName: str, handler: str, requestId: int) -> Battle:
        attacker = self._db.getUserSummaryByName(attackerName)
        if attacker is None:
            raise ValueError(f"Unknown attacker: {attackerName}")
        defender = self._db.getUserByName(defenderName)
        if defender is None:
            raise ValueError(f"Unknown defender: {defenderName}")
        battle = await self._db.getOrMakeBattle(attacker = attacker, defender = defender,
                handler = handler, requestId = requestId)
        return battle

    async def stopBattle(self, user: MutableUser):
        if not user.inBattle:
            raise UserNotInBattleException()
        await self.battleCoordinator.stopBattle(user.name)
        user.inBattle = False

    def clearInBattle(self):
        self._db.clearInBattle()

    async def accumulateGold(self):
        self.logger.info("accumulate_gold", -1, "Accumulating gold")
        await self._db.accumulateGold()
        self.logger.info("accumulate_gold", -1, "Done accumulating gold")

    def setBattleground(self, name: str, newBattleground: BattlegroundState):
        """Directly sets the Battleground for a given user. For test purposes only."""
        self._db.setBattleground(name, newBattleground)

    def resetBattles(self):
        self._db.resetBattles()

    async def resetGameData(self, uid: str):
        user = self._db.getUserSummaryByUid(uid)
        if not user.admin:
            raise UserNotAdminException()
        await self._db.resetGameData()
    
    def deleteAccount(self, uid: str):
        self._db.deleteAccount(uid)
        firebase_admin.auth.delete_user(uid)
    
    def getUserRivals(self, username: str) -> Rivals:
        return self._db.getUserRivals(username)
    
    async def calculateMissingBattles(self, requestId = -1):
        self.logger.info("calculate_missing_battles", requestId, "Finding missing battles.")
        missingBattles = self._db.findMissingBattles()
        awaitables = []
        for (attackerUid, defenderUid) in missingBattles:
            attacker = self._db.getUserSummaryByUid(attackerUid)
            defender = self._db.getUserByUid(defenderUid)
            awaitables.append(self._db.getOrMakeBattle(
                attacker, defender,
                requestId = requestId,
                handler = "calculate_missing_battles"))
        self.logger.info("calculate_missing_battles", requestId, "Calculating missing battles.")
        if awaitables:
            await asyncio.wait(awaitables)
        self._db.updateGoldPerMinuteOthers()
        # We intentionally don't update goldPerMinute self so players are
        # required to watch their battles themselves.
        self.logger.info("calculate_missing_battles", requestId, "Done.")