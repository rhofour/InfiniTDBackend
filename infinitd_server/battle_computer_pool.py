import asyncio
import concurrent.futures
from typing import List

from infinitd_server.battleground_state import BattlegroundState
from infinitd_server.battle_computer import BattleComputer, BattleCalcResults
from infinitd_server.game_config import GameConfig, ConfigId

def initWorker(gameConfig: GameConfig, gameTickSecs: float, debug: bool):
    global battleComputer
    battleComputer = BattleComputer(gameConfig, gameTickSecs, debug)

def computeBattle(battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:
    global battleComputer
    return battleComputer.computeBattle(battleground, wave)

class BattleComputerPool:
    executor: concurrent.futures.ProcessPoolExecutor

    def __init__(self, gameConfig: GameConfig, gameTickSecs: float = 0.01, debug = False):
        self.executor = concurrent.futures.ProcessPoolExecutor(
            initializer=initWorker,
            initargs=(gameConfig, gameTickSecs, debug),
            )

    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:
        concurrentFuture = self.executor.submit(computeBattle, battleground, wave)
        return asyncio.wrap_future(concurrentFuture)