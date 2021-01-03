import argparse
from dataclasses import dataclass, field
import json
import time
from typing import Optional, List, Dict
from pathlib import Path

import cattr
from dataclasses_json import dataclass_json, DataClassJsonMixin

from infinitd_server.game_config import GameConfig, GameConfigData, CellPos, ConfigId, Row, Col
from infinitd_server.battle import BattleResults
from infinitd_server.battleground_state import BattlegroundState, BgTowersState, BgTowerState

from infinitd_balancer.strategy import TowerPlacingStrategy, TowerSelectionStrategy, WaveSelectionStrategy, FullStrategy, GameState

class FixedWaveSelection(WaveSelectionStrategy):
    monsterIds: List[ConfigId]

    def __init__(self, gameConfig: GameConfig, monsterIds: List[ConfigId]):
        super().__init__(gameConfig)
        self.monsterIds = monsterIds

    def nextWave(self, battleground: BattlegroundState) -> List[ConfigId]:
        return self.monsterIds

class FixedOrderTowerPlacing(TowerPlacingStrategy):
    placingOrder: List[CellPos]

    def __init__(self, gameConfig, placingOrder: List[CellPos] = []):
        super().__init__(gameConfig)
        self.placingOrder = placingOrder.copy()
        # Reverse so we can just pop off the end.
        self.placingOrder.reverse()

    def nextPlace(self, battleground: BattlegroundState) -> Optional[CellPos]:
        if len(self.placingOrder) > 0:
            return self.placingOrder.pop()
        return None

class FixedTowerSelection(TowerSelectionStrategy):
    fixedTower: Optional[ConfigId]

    def __init__(self, gameConfig, fixedTower: Optional[str] = None):
        super().__init__(gameConfig)
        if fixedTower:
            self.fixedTower = gameConfig.nameToTowerId[fixedTower]
        else:
            self.fixedTower = None

    def nextTower(self, battleground: BattlegroundState) -> Optional[ConfigId]:
        return self.fixedTower

class HomogenousWaveSelection(WaveSelectionStrategy):
    monsterIds: List[ConfigId]

    def __init__(self, gameConfig: GameConfig, monsterNames: List[str]):
        super().__init__(gameConfig)
        self.monsterIds = [gameConfig.nameToMonsterId[name] for name in monsterNames]

    def nextWave(self, battleground: BattlegroundState) -> List[ConfigId]:
        bestWave = [self.monsterIds[0]]
        bestWaveResults = self.battleComputer.computeBattle(battleground, bestWave).results

        def computeBattle(newWave: List[ConfigId]) -> BattleResults:
            "Compute a new battle and potentially update best wave."
            nonlocal bestWave
            nonlocal bestWaveResults
            newWaveResults = self.battleComputer.computeBattle(battleground, newWave).results
            if newWaveResults.goldPerMinute > bestWaveResults.goldPerMinute:
                bestWave = newWave
                bestWaveResults = newWaveResults
            return newWaveResults

        for monsterId in self.monsterIds:
            # Lower bound wave should be the largest wave of this type we
            # can defeat.
            lowerBoundWave = [monsterId]
            lbWaveResults = computeBattle(lowerBoundWave)
            if not lbWaveResults.allMonstersDefeated():
                # If we can't defeat the first wave with this monster type
                # stop and return the best wave so far.
                return bestWave

            # Upper bound wave should be the smallest wave of this type we
            # cannot defeat in one minute.
            # Calculate an initial value by doubling the number of enemies
            # until we cannot beat the wave or it takes longer than one minute.
            upperBoundWave = [monsterId] * 8
            ubWaveResults = computeBattle(upperBoundWave)
            while ubWaveResults.allMonstersDefeated() and ubWaveResults.timeSecs <= 60.:
                # Reassign previous non-upper bound wave as the lower bound.
                lowerBoundWave = upperBoundWave
                lbWaveResults = ubWaveResults

                upperBoundWave = [monsterId] * (len(upperBoundWave) * 2)
                ubWaveResults = computeBattle(upperBoundWave)

            # Keep moving the waves closer together.
            while len(lowerBoundWave) + 1 < len(upperBoundWave):
                newSize = (len(lowerBoundWave) + len(upperBoundWave)) // 2
                newWave = [monsterId] * newSize
                newWaveResults = computeBattle(newWave)
                if (newWaveResults.allMonstersDefeated() and
                        newWaveResults.timeSecs <= 60.):
                    lowerBoundWave = newWave
                    lbWaveResults = newWaveResults
                else:
                    upperBoundWave = newWave
                    ubWaveResults = newWaveResults

            # If we cannot defeat upperBoundWave at all then stop searching.
            if not ubWaveResults.allMonstersDefeated():
                return bestWave

        # If we make it through all monster types just return the best wave
        # we've seen.
        return bestWave

@dataclass
@dataclass_json
class StrategyResults:
    results: Dict[str, List[GameState]]

    def __init__(self):
        self.results = {}

def main():
    gameConfigPath = Path('./game_config.json')
    with open(gameConfigPath) as gameConfigFile:
        gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
        gameConfig = GameConfig.fromGameConfigData(gameConfigData)

    # Build tower placement orders.
    # Assumes start is in the top-left and dest in the bottom-left.
    simpleRowOrder: List[ConfigId] = []
    for towerRow in range(gameConfig.playfield.numRows // 2):
        row = towerRow * 2 + 1
        colStart = towerRow % 2
        if row == gameConfig.playfield.numRows - 1:
            # Don't block the destination with the last row.
            colStart = 1
        for col in range(colStart, colStart + gameConfig.playfield.numCols - 1):
            simpleRowOrder.append(CellPos(Row(row), Col(col)))

    strategies: Dict[str, FullStrategy] = {
        'BalancedRows': FullStrategy(
            gameConfig,
            FixedOrderTowerPlacing(gameConfig, simpleRowOrder),
            FixedTowerSelection(gameConfig, "Paper Arrow Tower"),
            HomogenousWaveSelection(gameConfig, ["Dust Clump"])
        ),
        'FastRows': FullStrategy(
            gameConfig,
            FixedOrderTowerPlacing(gameConfig, simpleRowOrder),
            FixedTowerSelection(gameConfig, "Poking Tower"),
            HomogenousWaveSelection(gameConfig, ["Dust Bunny"])
        ),
        'SlowRows': FullStrategy(
            gameConfig,
            FixedOrderTowerPlacing(gameConfig, simpleRowOrder),
            FixedTowerSelection(gameConfig, "Brick Tower"),
            HomogenousWaveSelection(gameConfig, ["Dust Mass"])
        ),
    }

    strategyResults = StrategyResults()
    for (strategyName, strategy) in strategies.items():
        startTime = time.monotonic()
        results = strategy.evaluateUntil(1000)
        duration = time.monotonic() - startTime
        strategyResults.results[strategyName] = results
        print(f"{strategyName} ({duration:.1f}s)")
        for state in results:
            numTowers = 0
            for towersCol in state.battleground.towers.towers:
                for tower in towersCol:
                    if tower is not None:
                        numTowers += 1
            print(f"After {state.totalMinutes:3}m accumulated {state.accumulatedGold:3.1f} gold "
                f" and built {numTowers} towers. Future gold rate: {state.battleResults.goldPerMinute} gpm")

    with open('balancing_results.json', 'w') as outFile:
        outFile.write(strategyResults.to_json())

if __name__ == "__main__":
    main()
