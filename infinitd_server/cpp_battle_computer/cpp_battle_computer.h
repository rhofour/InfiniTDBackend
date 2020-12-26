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
  CppCellPos pos;
  float lastFired;
  float firingRadius; // How far a projectile from this tower could have traveled at this point.
  const TowerConfig& config;

  TowerState(int id_, int row, int col, const TowerConfig& config_) :
      id(id_), pos(row, col), firingRadius(0.0f), config(config_) {
    if (config_.firingRate > 0) {
      this->lastFired = -1.0f / config_.firingRate;
    } else {
      this->lastFired = -1.0f;
    }
  }
};

struct EnemyState {
  uint16_t id;

  CppCellPos pos;
  // For updating position.
  vector<CppCellPos>& path;
  uint16_t pathIdx;
  float lastPathTime;
  float nextPathTime;

  float health;
  float distTraveled;
  const EnemyConfig& config;

  EnemyState(int id_, vector<CppCellPos>& path_, float curTime, const EnemyConfig& config_) :
        id(id_), pos(path_[0]), path(path_), pathIdx(1), lastPathTime(curTime), health(config_.health),
        distTraveled(0), config(config_) {
    this->nextPathTime = curTime; // This will be updated when the enemy is first moved.
  }
};

class CppBattleComputer {
 public:
  GameConfig gameConfig;
  float gameTickSecs; // Period of the battle calculation clock

  CppBattleComputer() {};
  CppBattleComputer(string jsonText, float gameTickSecs_);
  string ComputeBattle(const vector<vector<int>>& towers, vector<int> wave,
    vector<vector<CppCellPos>> paths);
 private:
  vector<TowerState> getInitialTowerStates(const vector<vector<int>>& towerIds);
};