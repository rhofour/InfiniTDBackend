import asyncio
from typing import List, Optional, Awaitable, Callable
import math

from infinitdserver.battle import BattleCalculationException
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.db import Db, MutableUserContext
from infinitdserver.game_config import GameConfig
from infinitdserver.logger import Logger
from infinitdserver.sse import SseQueues
from infinitdserver.user import User, FrozenUser, FrozenUserSummary, MutableUser
from infinitdserver.paths import pathExists

class UserInBattleException(Exception):
    pass

class UserNotInBattleException(Exception):
    pass

class UserHasInsufficientGoldException(Exception):
    pass

class UserMatchingError(Exception):
    def __init__(self, actualName: str, expectedName: str):
        self.actualName = actualName
        self.expectedName = expectedName

    def __str__(self):
        return f"Expected username {self.expectedName}, got username {self.actualName}."

class Game:
    gameConfig: GameConfig
    battleQueues: SseQueues
    battlegroundQueues: SseQueues
    userQueues: SseQueues
    _battleCoordinator: BattleCoordinator
    _db: Db

    def __init__(self, gameConfig: GameConfig, debug: bool = False, dbPath = None):
        self.gameConfig = gameConfig
        self.logger = Logger.getDefault()

        # Make queues for streams
        self.battleQueues = SseQueues()
        self.battlegroundQueues = SseQueues()
        self.userQueues = SseQueues()

        self.battleCoordinator = BattleCoordinator(self.battleQueues)
        self._db = Db(
                gameConfig = self.gameConfig,
                userQueues = self.userQueues,
                bgQueues = self.battlegroundQueues,
                battleCoordinator = self.battleCoordinator,
                debug=debug,
                dbPath = dbPath)

    def getUserSummaries(self) -> List[FrozenUserSummary]:
        return self._db.getUsers()

    def getUserSummaryByName(self, name: str) -> Optional[FrozenUserSummary]:
        return self._db.getUserSummaryByName(name)

    def getUserSummaryByUid(self, uid: str) -> Optional[FrozenUserSummary]:
        return self._db.getUserSummaryByUid(uid)

    def getUserByUid(self, uid: str) -> Optional[User]:
        return self._db.getUserByUid(uid)

    def getMutableUserContext(self, uid: str, expectedName: str, addAwaitable: Callable[[Awaitable[None]], None]) -> MutableUserContext:
        mutableUserContext = self._db.getMutableUserContext(uid, addAwaitable)
        if mutableUserContext is None:
            raise ValueError(f"User with UID = {uid} not found.")
        # Compare against expected name
        if mutableUserContext.mutableUser.name != expectedName:
            raise UserMatchingError(actualName = mutableUserContext.mutableUser.name, expectedName = expectedName)
        # Build mutable user context
        return mutableUserContext

    def register(self, uid: str, name: str) -> bool:
        return self._db.register(uid=uid, name=name)

    def getBattleground(self, name: str) -> BattlegroundState:
        return self._db.getBattleground(name)

    def buildTower(self, user: MutableUser, row: int, col: int, towerId: int):
        try:
            towerConfig = self.gameConfig.towers[towerId]
        except IndexError:
            raise ValueError(f"Invalid tower ID {towerId}")

        if user.inBattle:
            raise UserInBattleException()

        if user.gold < towerConfig.cost:
            raise UserHasInsufficientGoldException(
                    f"{towerConfig.name} costs {towerConfig.cost}, but {user.name} only has {user.gold} gold.")

        existingTower = user.battleground.towers.towers[row][col]
        if existingTower:
            existingTowerName = self.gameConfig.towers[existingTower.id].name
            raise ValueError(f"{existingTowerName} already exists at row {row}, col {col}.")

        user.battleground.towers.towers[row][col] = BgTowerState(towerId)
        user.gold -= towerConfig.cost

        # Check if there is still a path from start to exit.
        blocked = not pathExists(user.battleground, self.gameConfig.playfield.monsterEnter, self.gameConfig.playfield.monsterExit)
        if blocked:
            user.resetBattleground() # Prevent us from writing back the changed battleground
            raise ValueError(f"Building at {row}, {col} would block the path.")

    def sellTower(self, user: MutableUser, row: int, col: int):
        if user.inBattle:
            raise UserInBattleException()

        existingTower: BgTowerState = user.battleground.towers.towers[row][col]
        if existingTower is None:
            raise ValueError(f"No tower exists at row {row}, col {col}.")
        try:
            towerConfig = self.gameConfig.towers[existingTower.id]
        except IndexError:
            # This should never happen as long as the game config matches the database.
            raise ValueError(f"Invalid tower ID {existingTower.id}")

        # Actually change the user
        user.battleground.towers.towers[row][col] = None # Does this work with the MutableUser stuff?
        sellAmount = math.floor(towerConfig.cost * self.gameConfig.misc.sellMultiplier)
        user.gold += sellAmount
        user.accumulatedGold += sellAmount

    def addToWave(self, user: MutableUser, monsterId: int):
        try:
            monsterConfig = self.gameConfig.monsters[monsterId]
        except IndexError:
            raise ValueError(f"Invalid monster ID {monsterId}")

        if user.inBattle:
            raise UserInBattleException()

        user.wave.append(monsterId)

    def clearWave(self, user: MutableUser):
        if user.inBattle:
            raise UserInBattleException()

        user.wave = []

    def joinBattle(self, name: str):
        return self.battleCoordinator.getBattle(name).join()

    async def startBattle(self, user: MutableUser, handler: str, requestId: int):
        if user.inBattle:
            raise UserInBattleException()

        user.inBattle = True
        # Manually update the user and end the transaction while the battle is
        # calculated. Since the user is marked as in battle none of their data
        # can change even outside of the transaction.
        awaitables: List[Awaitable[None]] = []
        def addAwaitable(a: Awaitable[None]):
            awaitables.append(a)
        self._db.updateUser(user, addAwaitable=addAwaitable)
        await asyncio.wait(awaitables)
        self._db.leaveTransaction()

        try:
            battle = self._db.getOrMakeBattle(user, handler=handler, requestId=requestId)
        except BattleCalculationException as e:
            self.logger.error()
            self._db.enterTransaction()
            user.inBattle = False

        # We need this because the user context is expecting to be in a
        # transaction at the end.
        self._db.enterTransaction()
        async def setUserNotInBattleCallback():
            await self._db.setUserNotInBattle(uid=user.uid, name=user.name)
        self.battleCoordinator.startBattle(user.name, battle.events, setUserNotInBattleCallback)

    async def stopBattle(self, user: MutableUser):
        if not user.inBattle:
            raise UserNotInBattleException()
        await self.battleCoordinator.stopBattle(user.name)
        user.inBattle = False

    def clearInBattle(self):
        self._db.clearInBattle()

    async def accumulateGold(self):
        await self._db.accumulateGold()

    async def setBattleground(self, name: str, newBattleground: BattlegroundState):
        """Directly sets the Battleground for a given user. For test purposes only."""
        await self._db.setBattleground(name, newBattleground)
