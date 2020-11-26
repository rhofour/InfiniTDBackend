# distutils: language = c++
# distutils: include_dirs = ./infinitd_server/cpp_battle_computer/rapidjson/include
from typing import List

import numpy as np

from libcpp.string cimport string
from libcpp.vector cimport vector

from infinitd_server.game_config import GameConfig, CellPos, ConfigId

cdef extern from "game_config.h":
    pass

cdef extern from "cpp_battle_computer.cpp":
    pass

cdef extern from "cpp_battle_computer.h":
    cdef struct CppCellPos:
        float row
        float col

    cdef cppclass CppBattleComputer:
        CppBattleComputer() except +
        CppBattleComputer(string) except +
        void ComputeBattle(const vector[vector[int]]&, vector[int] wave,
                vector[vector[CppCellPos]])

cdef vector[CppCellPos] _pathToCpp(pyPath):
    cdef vector[CppCellPos] cppPath
    for pyPos in pyPath:
        cppPath.push_back(CppCellPos(pyPos.row, pyPos.col))
    return cppPath

cdef class BattleComputer:
    cdef CppBattleComputer cppBattleComputer
    cdef object gameConfig

    def __init__(self, gameConfig: GameConfig, jsonStr: str):
        self.gameConfig = gameConfig
        self.cppBattleComputer = CppBattleComputer(jsonStr.encode("UTF-8"))

    def computeBattle(self, battleground, wave: List[ConfigId], paths: List[List[CellPos]]):
        if not wave:
            raise ValueError("Cannot compute battle with empty wave.")

        # Convert battleground into a Numpy array.
        numRows = self.gameConfig.playfield.numRows
        numCols = self.gameConfig.playfield.numCols

        towers = np.full((numRows, numCols), -1)
        for (row, rowTowers) in enumerate(battleground.towers.towers):
            for (col, tower) in enumerate(rowTowers):
                if tower is not None:
                    towers[row, col] = tower.id

        # Convert paths into a vector of vectors
        cdef vector[vector[CppCellPos]] cppPaths
        for pyPath in paths:
            cppPaths.push_back(_pathToCpp(pyPath))

        # Actually call the C++ code
        self.cppBattleComputer.ComputeBattle(towers, wave, cppPaths)
