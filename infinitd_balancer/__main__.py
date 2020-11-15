import argparse
import json
from typing import Optional, List, Dict
from pathlib import Path

import cattr

from infinitdserver.game_config import GameConfig, GameConfigData, CellPos, ConfigId
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState

from infinitd_balancer.strategy import TowerPlacingStrategy, TowerSelectionStrategy, WaveSelectionStrategy, FullStrategy

class DoNothingTowerPlacing(TowerPlacingStrategy):
    def nextPlace(self, battleground: BattlegroundState) -> Optional[CellPos]:
        return None

class DoNothingTowerSelection(TowerSelectionStrategy):
    def nextTower(self, battleground: BattlegroundState) -> Optional[ConfigId]:
        return None

class FixedWaveSelection(WaveSelectionStrategy):
    monsterIds: List[ConfigId]

    def __init__(self, gameConfig: GameConfig, monsterIds: List[ConfigId]):
        super().__init__(gameConfig)
        self.monsterIds = monsterIds

    def nextWave(self, battleground: BattlegroundState) -> List[ConfigId]:
        return self.monsterIds

def main():
    gameConfigPath = Path('./game_config.json')
    with open(gameConfigPath) as gameConfigFile:
        gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
        gameConfig = GameConfig.fromGameConfigData(gameConfigData)

    strategies: Dict[str, FullStrategy] = {
        'DoNothing': FullStrategy(
            gameConfig,
            DoNothingTowerPlacing(gameConfig),
            DoNothingTowerSelection(gameConfig),
            FixedWaveSelection(gameConfig, [ConfigId(0)])
        ),
    }

    for (strategyName, strategy) in strategies.items():
        results = strategy.evaluateUntil(1000)
        print(strategyName)
        print(results)

if __name__ == "__main__":
    main()
