#include "cpp_battle_computer.h"

#include <string>
#include <iostream>
#include <sstream>

#include "rapidjson/document.h"
#include "rapidjson/error/en.h"

using std::cout;
using std::cerr;
using std::endl;
using std::stringstream;
using rapidjson::Document;
using InfiniTDFb::BattleEventFb;
using InfiniTDFb::MonsterDefeatedFb;
using InfiniTDFb::MonstersDefeatedFb;
using InfiniTDFb::CreateMonstersDefeatedFb;
using InfiniTDFb::CreateBattleEventFb;
using InfiniTDFb::CreateBattleCalcResultsFb;

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

vector<TowerState> CppBattleComputer::getInitialTowerStates(const vector<vector<int>>& towerIds) {
  vector<TowerState> towers;
  uint16_t nextId = 0;
  int row = 0;
  for (const vector<int>& idsRow : towerIds) {
    int col = -1;
    for (const int towerId : idsRow) {
      col++;
      if (towerId == -1) continue;
      try {
        TowerConfig &towerConfig = this->gameConfig.towers.at(towerId);
        towers.emplace_back(nextId++, row, col, towerConfig);
      }
      catch (const std::out_of_range& e) {
        stringstream ss;
        ss << "Could not find tower with ID: " << towerId;
        throw ss.str();
      }
    }
    row++;
  }
  return towers;
}

string CppBattleComputer::ComputeBattle(
    const vector<vector<int>>& towerIds,
    vector<int> wave,
    vector<vector<CppCellPos>> paths) {
  const int numRows = towerIds.size();
  const int numCols = towerIds[0].size();
  cout << "Computing a " << numRows << " x " << numCols
    << " battle with " << wave.size() << " enemies and "
    << paths.size() << " paths." << endl;

  string errStr;
  try {
    // Initialize tower states.
    vector<TowerState> towers = this->getInitialTowerStates(towerIds);

    // Store enemies in reverse order so we can efficiently remove from the end.
    vector<int> unspawnedEnemies(wave.crbegin(), wave.crend());

    // Main game loop
    uint16_t nextId = 0;
    float gameTime = 0.0;
    uint16_t ticks = 0;
    while (!unspawnedEnemies.empty()) {
      // Spawn new enemy
      int enemyConfigId = unspawnedEnemies.back();
      unspawnedEnemies.pop_back();
    }
  }
  catch (string err) {
    cerr << err << endl;
    errStr = err;
  }

  // First, serialize the events into a BattleEventsFb.
  flatbuffers::FlatBufferBuilder eventsBuilder(1024);
  vector<flatbuffers::Offset<BattleEventFb>> eventOffsets;
  auto eventsFb = eventsBuilder.CreateVector(eventOffsets);
  auto battleEventsFb = CreateBattleEventsFb(eventsBuilder, eventsFb);
  eventsBuilder.Finish(battleEventsFb);

  flatbuffers::FlatBufferBuilder builder(1024);
  builder.ForceVectorAlignment(eventsBuilder.GetSize(), sizeof(uint8_t),
    eventsBuilder.GetBufferMinAlignment());
  auto errStrOffset = builder.CreateString(errStr);
  vector<MonsterDefeatedFb> monsterDefeatedFbs;
  auto monstersDefeatedVector = builder.CreateVectorOfStructs(monsterDefeatedFbs);
  auto monstersDefeatedFb = CreateMonstersDefeatedFb(builder, monstersDefeatedVector);
  auto eventBytesFb = builder.CreateVector(eventsBuilder.GetBufferPointer(), eventsBuilder.GetSize());
  auto result = CreateBattleCalcResultsFb(builder, errStrOffset, monstersDefeatedFb, eventBytesFb);
  builder.Finish(result);
  // Copy the created buffer into a std::string to pass to Python.
  string bytes((const char*)builder.GetBufferPointer(), builder.GetSize());
  return bytes;
}