# distutils: language = c++
# distutils: include_dirs = ./infinitd_server/cpp_battle_computer/rapidjson/include

from libcpp.string cimport string

cdef extern from "game_config.h":
  pass

cdef extern from "cpp_battle_computer.cpp":
  pass

cdef extern from "cpp_battle_computer.h":
  cdef cppclass CppBattleComputer:
    CppBattleComputer() except +
    CppBattleComputer(string) except +
    void ComputeBattle(int)

cdef class BattleComputer:
  cdef CppBattleComputer cpp_battle_computer

  def __init__(self, jsonStr):
    self.cpp_battle_computer = CppBattleComputer(jsonStr.encode("UTF-8"))

  def computeBattle(self, battleground, wave, int seed):
    self.cpp_battle_computer.ComputeBattle(seed)
