import argparse
import json
from typing import Optional, List, Dict
from pathlib import Path

import cattr

from infinitdserver.game_config import GameConfig, GameConfigData, CellPos, ConfigId, Row, Col
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState

from infinitd_balancer.strategy import TowerPlacingStrategy, TowerSelectionStrategy, WaveSelectionStrategy, FullStrategy

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

    def __init__(self, gameConfig, fixedTower: Optional[ConfigId] = None):
        super().__init__(gameConfig)
        self.fixedTower = fixedTower

    def nextTower(self, battleground: BattlegroundState) -> Optional[ConfigId]:
        return self.fixedTower

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
    print(f"For a playfield of {gameConfig.playfield.numCols} cols by "
            f"{gameConfig.playfield.numRows} rows: "
            f"came up with order: {simpleRowOrder}")

    strategies: Dict[str, FullStrategy] = {
        'DoNothing': FullStrategy(
            gameConfig,
            FixedOrderTowerPlacing(gameConfig),
            FixedTowerSelection(gameConfig),
            FixedWaveSelection(gameConfig, [ConfigId(0)])
        ),
        'SimpleRows': FullStrategy(
            gameConfig,
            FixedOrderTowerPlacing(gameConfig, simpleRowOrder),
            FixedTowerSelection(gameConfig, ConfigId(0)),
            FixedWaveSelection(gameConfig, [ConfigId(0)])
        ),
    }

    for (strategyName, strategy) in strategies.items():
        results = strategy.evaluateUntil(1000)
        print(strategyName)
        for state in results:
            numTowers = 0
            for towersCol in state.battleground.towers.towers:
                for tower in towersCol:
                    if tower is not None:
                        numTowers += 1
            print(f"After {state.totalMinutes:3}m accumulated {state.accumulatedGold:3.1f} gold "
                f"({state.goldPerMinute} / m) and built {numTowers} towers.")

if __name__ == "__main__":
    main()
