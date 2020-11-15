import argparse
import json

import cattr

from infinitdserver.game_config import GameConfig, GameConfigData

from infinitd_balancer.strategy import TowerPlacingStrategy, TowerSelectionStrategy, WaveSelectionStrategy, FullStrategy

def main():
    with open('../infinitdserver/game_config.json') as gameConfigFile:
        gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
        gameConfig = GameConfig.fromGameConfigData(gameConfigData)

if __name__ == "__main__":
    main()
