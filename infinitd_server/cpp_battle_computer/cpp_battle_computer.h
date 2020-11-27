#pragma once
#include <string>
#include <vector>

#include "types.h"
#include "game_config.h"
#include "battle_event.h"

using std::string;
using std::vector;

struct CppBattleCalcResult {
  vector<CppBattleEvent> events;
};

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  CppBattleComputer() {};
  CppBattleComputer(string jsonText);
  CppBattleCalcResult ComputeBattle(const vector<vector<int>>& towers, vector<int> wave,
      vector<vector<CppCellPos>> paths);
};
