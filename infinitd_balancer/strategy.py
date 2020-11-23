import abc
from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Tuple, List, Optional

import cattr
from dataclasses_json import dataclass_json, config, config

from infinitd_server.game_config import GameConfig, CellPos, ConfigId, TowerConfig, MonsterConfig
from infinitd_server.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitd_server.battle import BattleResults
from infinitd_server.battle_computer import BattleComputer

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
@dataclass_json
class GameState:
    accumulatedGold: float
    currentGold: float
    battleResults: BattleResults = field(
        metadata = config(
            encoder=cattr.unstructure,
            decoder=lambda x: cattr.structure(x, BattleResults),
        )
    )
    battleground: BattlegroundState
    wave: List[ConfigId]
    totalMinutes: int = 0

    def __init__(self, startingGold, battleResults, battleground, wave):
        self.accumulatedGold = startingGold
        self.currentGold = startingGold
        self.battleResults = battleResults
        self.battleground = battleground
        self.wave = wave

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
        # Run at slightly lower precision to speed up the balancing
        self.battleComputer = BattleComputer(gameConfig, gameTickSecs=0.02)

    def evaluateUntil(self, targetGold: int) -> List[GameState]:
        "evaluateUntil returns how many minutes until targetGold is accumulated."
        # fakeResults that always result in getting minGoldPerMinute.
        fakeResults = BattleResults({}, [], self.gameConfig.misc.minGoldPerMinute, 60.)
        curState: GameState = GameState(
                self.gameConfig.misc.startingGold,
                fakeResults,
                BattlegroundState.empty(self.gameConfig),
                [],
            )
        history: List[GameState] = []

        def updateBattle(battleground) -> Tuple[List[ConfigId], BattleResults]:
            "updateBattle takes a battleground and gets a new wave and battle."
            wave = self.waveSelectionStrategy.nextWave(battleground)
            battleCalcResults = self.battleComputer.computeBattle(battleground, wave)
            results = battleCalcResults.results
            return (wave, results)

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
                curState.wave, curState.battleResults = updateBattle(curState.battleground)
                # Update history every time we calculate a new battle
                history.append(deepcopy(curState))

                # Wait some number of minutes
                waitedMins = math.ceil((nextTowerCost - curState.currentGold) /
                        curState.battleResults.goldPerMinute)
                curState.totalMinutes += waitedMins
                curState.accumulatedGold += waitedMins * curState.battleResults.goldPerMinute
                curState.currentGold += waitedMins * curState.battleResults.goldPerMinute

            # Buy the new tower and loop again
            curState.currentGold -= nextTowerCost
            curState.battleground.towers.towers[nextTowerLoc.row][nextTowerLoc.col] = BgTowerState(
                    id = nextTowerId)

        if curState.accumulatedGold < targetGold:
            # Update the battle one last time
            curState.wave, curState.battleResults = updateBattle(curState.battleground)
            # Update history every time we calculate a new battle
            history.append(deepcopy(curState))

            remainingGold = targetGold - curState.accumulatedGold
            minutesAtEnd = math.ceil(float(remainingGold) / curState.battleResults.goldPerMinute)
            curState.totalMinutes += minutesAtEnd
            curState.accumulatedGold += minutesAtEnd * curState.battleResults.goldPerMinute
            curState.currentGold += minutesAtEnd * curState.battleResults.goldPerMinute

        history.append(curState)
        return history
