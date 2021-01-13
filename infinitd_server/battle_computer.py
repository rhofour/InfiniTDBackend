from dataclasses import dataclass, asdict
from random import Random
import math
from typing import List, Optional, Tuple, Sequence
import json

import cattr
import flatbuffers

from infinitd_server.battle import ObjectType, EventType, MoveEvent, DeleteEvent, DamageEvent, BattleResults, Battle, FpCellPos, BattleEvent, FpRow, FpCol, BattleCalcResults
from infinitd_server.battleground_state import BattlegroundState, BgTowerState
from infinitd_server.game_config import GameConfig, TowerConfig, CellPos, MonsterConfig, ConfigId, MonstersDefeated
from infinitd_server.paths import PathMap, makePathMap, compressPath
from infinitd_server.cpp_battle_computer.battle_computer import BattleComputer as CppBattleComputer
import  InfiniTDFb.BattleCalcResultsFb as BattleCalcResultsFb
import  InfiniTDFb.BattleEventsFb as BattleEventsFb

EVENT_PRECISION = 4 # Number of decimal places to use for events

class BattleCalculationException(Exception):
    def __init__(self, battleground: BattlegroundState, wave: List[ConfigId], message: str):
        self.battleground_json = battleground.to_json()
        self.message = message

@dataclass(frozen=False)
class TowerState:
    id: int
    config: TowerConfig
    pos: FpCellPos
    lastFired: float
    firingRadius: float = -1 # How far a projectile could have travelled at this point
    firingRadiusSq: float = -1

@dataclass(frozen=False)
class MonsterState:
    id: int
    config: MonsterConfig
    pos: FpCellPos
    health: float
    path: List[CellPos]
    spawnedAt: float
    targetInPath: int = 1
    distTraveled: float = 0.0

class BattleComputer:
    gameConfig: GameConfig
    gameTickSecs: float # Period of the gameplay clock
    debug: bool
    cppBattleComputer: CppBattleComputer

    def __init__(self, gameConfig: GameConfig, gameTickSecs: float = 0.01, debug = False):
        self.gameConfig = gameConfig
        self.gameTickSecs = gameTickSecs
        self.debug = debug
        jsonText = json.dumps(cattr.unstructure(gameConfig.gameConfigData))
        self.cppBattleComputer = CppBattleComputer(gameConfig, jsonText, gameTickSecs)

    def getInitialTowerStates(self, battleground: BattlegroundState) -> List[TowerState]:
        nextId = 0
        towerStates = []
        for (row, towersCol) in enumerate(battleground.towers.towers):
            for (col, maybeTower) in enumerate(towersCol):
                if maybeTower is None:
                    continue
                config = self.gameConfig.towers[maybeTower.id]
                towerStates.append(
                    TowerState(
                        id = nextId,
                        config = config,
                        pos = FpCellPos(FpRow(row), FpCol(col)),
                        lastFired = -(1 / config.firingRate) if config.firingRate > 0 else -1,
                    )
                )
                nextId += 1
        return towerStates

    @staticmethod
    def selectTarget(tower: TowerState, enemies: Sequence[MonsterState], gameTime: float
            ) -> Optional[Tuple[MonsterState, float]]:

        if tower.firingRadius <= 0:
            return None

        for enemy in enemies:
            distSq = enemy.pos.distSq(tower.pos)
            if distSq <= tower.firingRadiusSq:
                dist = math.sqrt(distSq)
                timeToHit = dist / tower.config.projectileSpeed
                if gameTime - timeToHit < enemy.spawnedAt:
                    continue # Don't allow targetting enemies before they've spawned.
                # Assumes enemies are sorted by decreasing distTraveled so we
                # can return the first one we can hit.
                return (enemy, dist)

        return None

    def computeBattle(self, battleground: BattlegroundState, wave: List[ConfigId]) -> BattleCalcResults:
        if not wave:
            raise ValueError("Cannot compute battle with empty wave.")

        pathMap = makePathMap(
                battleground,
                self.gameConfig.playfield.monsterEnter,
                self.gameConfig.playfield.monsterExit)
        if not pathMap:
            raise ValueError("Cannot compute battle with no path.")

        # Make any changes to the wave or towers change the paths enemies take.
        flattenedBattleground = []
        for row in battleground.towers.towers:
            for maybeTower in row:
                if maybeTower is None:
                    flattenedBattleground.append(-1)
                else:
                    flattenedBattleground.append(maybeTower.id)
        battlegroundWaveTuple = (tuple(flattenedBattleground), tuple(wave))
        rand = Random(hash(battlegroundWaveTuple))
        # Calculate paths for all enemies ahead of time.
        paths = []
        for _ in wave:
            paths.append(compressPath(pathMap.getRandomPath(
                self.gameConfig.playfield.monsterEnter, rand)))

        result = self.cppBattleComputer.computeBattle(battleground, wave, paths)
        battleCalcFb = BattleCalcResultsFb.BattleCalcResultsFb.GetRootAsBattleCalcResultsFb(result, 0)
        if cppErr := battleCalcFb.Error():
            raise BattleCalculationException(battleground, wave, cppErr)

        # Calculate bonuses using monstersDefeated
        battleResults = BattleResults.fromMonstersDefeatedFb(
                battleCalcFb.MonstersDefeated(),
                self.gameConfig, round(battleCalcFb.TimeSecs(), EVENT_PRECISION))

        return BattleCalcResults(
                fb = battleCalcFb,
                results = battleResults,
            )
