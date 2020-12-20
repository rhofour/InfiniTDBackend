#pragma once
#include <string>
#include <vector>

#include "types.h"
#include "game_config.h"
#include "../../battle_generated.h"

using std::string;
using std::vector;
using InfiniTDFb::BattleCalcResultsFb;

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  CppBattleComputer() {};
  CppBattleComputer(string jsonText);
  string ComputeBattle(const vector<vector<int>>& towers, vector<int> wave,
      vector<vector<CppCellPos>> paths);
};
