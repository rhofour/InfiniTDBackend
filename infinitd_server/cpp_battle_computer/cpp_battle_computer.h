#pragma once
#include <string>
#include <vector>

#include "game_config.h"

using std::string;
using std::vector;

struct CppCellPos {
  float row, col;
};

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  CppBattleComputer() {};
  CppBattleComputer(string jsonText);
  void ComputeBattle(const vector<vector<int>>& towers, vector<int> wave,
      vector<vector<CppCellPos>> paths);
};
