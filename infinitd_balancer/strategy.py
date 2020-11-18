import abc
from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Tuple, List, Optional

from infinitdserver.game_config import GameConfig, CellPos, ConfigId, TowerConfig, MonsterConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.battle_computer import BattleComputer

class TowerPlacingStrategy(metaclass=abc.ABCMeta):
    "A TowerPlacingStrategy determines where to place new towers."
    gameConfig: GameConfig

    def __init__(self, gameConfig: GameConfig):
        self.gameConfig = gameConfig

    @abc.abstractmethod
    def nextPlace(self, battleground: BattlegroundState) -> Optional[CellPos]:
        pass

class TowerSelectionStrategy(metaclass=abc.ABCMeta):
    "A TowerSelectionStrategy determines which towers to place."
    gameConfig: GameConfig

    def __init__(self, gameConfig: GameConfig):
        self.gameConfig = gameConfig

    @abc.abstractmethod
    def nextTower(self, battleground: BattlegroundState) -> Optional[ConfigId]:
        pass

class WaveSelectionStrategy(metaclass=abc.ABCMeta):
    "A WaveSelectionStrategy selects a wave based on a battleground."
    gameConfig: GameConfig
    battleComputer: BattleComputer

    def __init__(self, gameConfig: GameConfig):
        self.gameConfig = gameConfig
        self.battleComputer = BattleComputer(gameConfig, True)

    @abc.abstractmethod
    def nextWave(self, battleground: BattlegroundState) -> List[ConfigId]:
        pass

@dataclass
class GameState:
    accumulatedGold: float
    currentGold: float
    goldPerMinute: float
    battleground: BattlegroundState
    totalMinutes: int = 0

    def __init__(self, startingGold, goldPerMinute, battleground):
        self.accumulatedGold = startingGold
        self.currentGold = startingGold
        self.goldPerMinute = goldPerMinute
        self.battleground = battleground

class FullStrategy:
    gameConfig: GameConfig
    placingStrategy: TowerPlacingStrategy
    towerSelectionStrategy: TowerSelectionStrategy
    waveSelectionStrategy: WaveSelectionStrategy
    battleComputer: BattleComputer

    def __init__(self,
            gameConfig: GameConfig,
            placingStrategy: TowerPlacingStrategy,
            towerSelectionStrategy: TowerSelectionStrategy,
            waveSelectionStrategy: WaveSelectionStrategy):
        self.gameConfig = gameConfig
        self.placingStrategy = placingStrategy
        self.towerSelectionStrategy = towerSelectionStrategy
        self.waveSelectionStrategy = waveSelectionStrategy
        self.battleComputer = BattleComputer(gameConfig)

    def evaluateUntil(self, targetGold: int) -> List[GameState]:
        "evaluateUntil returns how many minutes until targetGold is accumulated."
        curState: GameState = GameState(
                self.gameConfig.misc.startingGold,
                self.gameConfig.misc.minGoldPerMinute,
                BattlegroundState.empty(self.gameConfig)
            )
        history: List[GameState] = []

        def updateBattle(battleground) -> float:
            "updateBattle takes a battleground and gets a new goldPerMinute value."
            wave = self.waveSelectionStrategy.nextWave(battleground)
            battleCalcResults = self.battleComputer.computeBattle(battleground, wave)
            results = battleCalcResults.results
            # Be sure to keep this in sync with the game
            minutes = max(1.0, results.timeSecs / 60.0)
            return round(results.reward / minutes, ndigits = 1)

        while curState.accumulatedGold < targetGold:
            nextTowerLoc = self.placingStrategy.nextPlace(curState.battleground)
            if nextTowerLoc is None:
                break

            nextTowerId = self.towerSelectionStrategy.nextTower(curState.battleground)
            if nextTowerId is None:
                break

            nextTowerConfig = self.gameConfig.towers[nextTowerId]
            nextTowerCost = nextTowerConfig.cost

            # TODO: If this is an existing tower and next tower is different
            # then sell this.
            prevTowerId = curState.battleground.towers.towers[nextTowerLoc.row][nextTowerLoc.col]
            if prevTowerId:
                raise Exception(f"nextTowerLoc is already occupied by {prevTowerId}")

            if curState.currentGold < nextTowerCost:
                # Select a wave for the current battleground
                curState.goldPerMinute = updateBattle(curState.battleground)
                # Update history every time we calculate a new battle
                history.append(deepcopy(curState))

                # Wait some number of minutes
                waitedMins = math.ceil((nextTowerCost - curState.currentGold) /
                        curState.goldPerMinute)
                curState.totalMinutes += waitedMins
                curState.accumulatedGold += waitedMins * curState.goldPerMinute
                curState.currentGold += waitedMins * curState.goldPerMinute

            # Buy the new tower and loop again
            curState.currentGold -= nextTowerCost
            curState.battleground.towers.towers[nextTowerLoc.row][nextTowerLoc.col] = BgTowerState(
                    id = nextTowerId)

        if curState.accumulatedGold < targetGold:
            # Update the battle one last time
            curState.goldPerMinute = updateBattle(curState.battleground)
            # Update history every time we calculate a new battle
            history.append(deepcopy(curState))

            remainingGold = targetGold - curState.accumulatedGold
            minutesAtEnd = math.ceil(float(remainingGold) / curState.goldPerMinute)
            curState.totalMinutes += minutesAtEnd
            curState.accumulatedGold += minutesAtEnd * curState.goldPerMinute
            curState.currentGold += minutesAtEnd * curState.goldPerMinute

        history.append(curState)
        return history
