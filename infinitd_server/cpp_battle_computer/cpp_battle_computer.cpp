#include "cpp_battle_computer.h"

#include <iostream>

#include "rapidjson/document.h"
#include "rapidjson/error/en.h"

using std::cout;
using std::cerr;
using std::endl;
using rapidjson::Document;

CppBattleComputer::CppBattleComputer(std::string jsonText) {
  Document d;
  if (d.Parse(jsonText.c_str()).HasParseError()) {
    cerr << "Error parsing JSON (offset " <<
      (unsigned)d.GetErrorOffset() << "): " <<
      GetParseError_En(d.GetParseError()) << endl;
    throw d.GetParseError();
  }
  this->gameConfig = GameConfig(d);
}

CppBattleCalcResult CppBattleComputer::ComputeBattle(
    const vector<vector<int>>& towers,
    vector<int> wave,
    vector<vector<CppCellPos>> paths) {
  const int numRows = towers.size();
  const int numCols = towers[0].size();
  cout << "Computing a " << numRows << " x " << numCols
    << " battle with " << wave.size() << " enemies and "
    << paths.size() << " paths." << endl;

  CppBattleCalcResult result;

  // Initialize tower states.

  // Store enemies in reverse order so we can efficiently remove from the end.
  vector<int> unspawnedEnemies(wave.crbegin(), wave.crend());

  // Main game loop
  while (!unspawnedEnemies.empty()) {
    // Spawn new enemy
    int enemyConfigId = unspawnedEnemies.back();
    unspawnedEnemies.pop_back();
  }

  return result;
}
