#pragma once
#include "game_config.h"

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  CppBattleComputer() {};
  CppBattleComputer(std::string jsonText);
  void ComputeBattle(int seed);
};
