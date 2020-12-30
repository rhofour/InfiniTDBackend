import argparse
import json
import time
from pathlib import Path

import cattr

from infinitd_server.game_config import GameConfig, GameConfigData, CellPos, ConfigId, Row, Col
from infinitd_server.battle import Battle
from infinitd_server.battleground_state import BattlegroundState
from infinitd_server.battle_computer import BattleComputer

def main():
    parser = argparse.ArgumentParser(
            description="Small script to time battle calculation.")
    parser.add_argument('battleInputFile', metavar='file', type=str,
            help="A JSON file containing a battleground and wave.")
    parser.add_argument('-i', '--iters', action="store", type=int, default=1)
    args = parser.parse_args()

    gameConfigPath = Path('./game_config.json')
    with open(gameConfigPath) as gameConfigFile:
        gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
        gameConfig = GameConfig.fromGameConfigData(gameConfigData)

    # Decode battle input from file
    with open(args.battleInputFile) as battleInputFile:
        battleInput = json.loads(battleInputFile.read())
    battleground = BattlegroundState.from_dict(battleInput['battleground'])
    wave = battleInput['wave']

    battleComputer = BattleComputer(gameConfig, debug=False)
    startTime = time.monotonic()
    for _ in range(args.iters):
        battleComputer.computeBattle(battleground, wave)
        duration = time.monotonic() - startTime

    print(f"Computed the {args.iters} battles in {duration:.3f}s "
        f"({duration / args.iters:.4f}s each)")

if __name__ == "__main__":
    main()
