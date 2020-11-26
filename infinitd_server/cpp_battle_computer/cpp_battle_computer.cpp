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

void CppBattleComputer::ComputeBattle(
    const vector<vector<int>>& towers,
    vector<int> wave,
    vector<vector<CppCellPos>> paths) {
  const int numRows = towers.size();
  const int numCols = towers[0].size();
  cout << "Computing a " << numRows << " x " << numCols
    << " battle with " << wave.size() << " enemies and "
    << paths.size() << " paths." << endl;
}
