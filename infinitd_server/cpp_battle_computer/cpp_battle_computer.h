#pragma once
#include <string>
#include <vector>

#include "types.h"
#include "game_config.h"
#include "../../battle_generated.h"

using std::string;
using std::vector;
using InfiniTDFb::BattleCalcResultsFb;

struct TowerState {
  uint16_t id;
  float posRow;
  float posCol;
  float lastFired;
  float firingRadius; // How far a projectile from this tower could have traveled at this point.
  const TowerConfig& config;

  TowerState(int id_, int row, int col, const TowerConfig& config_) :
      id(id_), posRow(row), posCol(col), firingRadius(0.0f), config(config_) {
    if (config_.firingRate > 0) {
      this->lastFired = -1.0f / config_.firingRate;
    } else {
      this->lastFired = -1.0f;
    }
  }
};

struct EnemyState {
  uint16_t id;
  float posRow;
  float posCol;
  float health;
  float distTraveled;
  const EnemyConfig& config;

  EnemyState(int id_, int row, int col, const EnemyConfig& config_) :
      id(id_), posRow(row), posCol(col), config(config_) {          
    health = config.health;
    distTraveled = 0;
  }
};

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  CppBattleComputer() {};
  CppBattleComputer(string jsonText);
  string ComputeBattle(const vector<vector<int>>& towers, vector<int> wave,
    vector<vector<CppCellPos>> paths);
 private:
  vector<TowerState> getInitialTowerStates(const vector<vector<int>>& towerIds);
};