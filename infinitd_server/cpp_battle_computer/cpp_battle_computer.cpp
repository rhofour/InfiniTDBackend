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
using InfiniTDFb::FpCellPosFb;
using InfiniTDFb::ObjectTypeFb;
using InfiniTDFb::BattleEventFb;
using InfiniTDFb::BattleEventUnionFb;
using InfiniTDFb::BattleEventUnionFbUnion;
using InfiniTDFb::BattleEventFbT;
using InfiniTDFb::DeleteEventFbT;
using InfiniTDFb::DamageEventFbT;
using InfiniTDFb::MoveEventFbT;
using InfiniTDFb::MonsterDefeatedFb;
using InfiniTDFb::MonstersDefeatedFb;
using InfiniTDFb::CreateMonstersDefeatedFb;
using InfiniTDFb::CreateBattleEventFb;
using InfiniTDFb::CreateBattleCalcResultsFb;

CppBattleComputer::CppBattleComputer(std::string jsonText, float gameTickSecs_) :
    gameTickSecs(gameTickSecs_) {
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
        const TowerConfig &towerConfig = this->gameConfig.towers.at(towerId);
        TowerState towerState = TowerState(nextId++, row, col, towerConfig);
        towers.push_back(towerState);
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

// For sorting the events.
float GetStartTime(const BattleEventFbT &event) {
  const MoveEventFbT *moveEvent = event.event.AsMove();
  if (moveEvent) return moveEvent->start_time;
  const DeleteEventFbT *deleteEvent = event.event.AsDelete();
  if (deleteEvent) return deleteEvent->start_time;
  const DamageEventFbT *damageEvent = event.event.AsDamage();
  if (damageEvent) return damageEvent->start_time;

  assert(false);
  return -1.0;
}

void MoveEnemies(float gameTime, vector<EnemyState> &enemies, vector<BattleEventFbT> &events,
    vector<size_t> &removedEnemyIdx) {
  size_t enemyIdx = -1; // Intentional overflow so the first real value is 0.
  for (EnemyState &enemy : enemies) {
    enemyIdx++;
    if (enemy.nextPathTime <= gameTime) {
      // Update path and make a new move event.

      // First, add remaining bit of path to distTraveled.
      enemy.distTraveled += enemy.pos.dist(enemy.path.get()[enemy.pathIdx]);

      // Check if we've reached the destination.
      assert(enemy.pathIdx < enemy.path.get().size());
      if (enemy.pathIdx == enemy.path.get().size() - 1) {
        // Remove this enemy.
        DeleteEventFbT deleteEvent;
        deleteEvent.obj_type = ObjectTypeFb::ObjectTypeFb_ENEMY;
        deleteEvent.id = enemy.id;
        deleteEvent.start_time = enemy.nextPathTime;
        BattleEventFbT battleEvent;
        BattleEventUnionFbUnion battleEventUnion;
        battleEventUnion.Set(deleteEvent);
        battleEvent.event = battleEventUnion;
        events.push_back(battleEvent);

        removedEnemyIdx.push_back(enemyIdx);
        continue;
      }
      // Otherwise make a new move event.
      MoveEventFbT moveEvent;
      moveEvent.obj_type = ObjectTypeFb::ObjectTypeFb_ENEMY;
      moveEvent.id = enemy.id;
      moveEvent.config_id = enemy.config.get().id;
      moveEvent.start_time = enemy.nextPathTime;
      const CppCellPos &prevDest = enemy.path.get()[enemy.pathIdx];
      moveEvent.start_pos = FpCellPosFb(prevDest.row, prevDest.col);
      const CppCellPos nextDest = enemy.path.get()[enemy.pathIdx + 1];
      float timeToDest = prevDest.dist(nextDest) / enemy.config.get().speed;
      moveEvent.dest_pos = FpCellPosFb(nextDest.row, nextDest.col);
      moveEvent.end_time = enemy.nextPathTime + timeToDest;
      // TODO: refactor this out into an AddEvent method
      BattleEventFbT battleEvent;
      BattleEventUnionFbUnion battleEventUnion;
      battleEventUnion.Set(moveEvent);
      battleEvent.event = battleEventUnion;
      events.push_back(battleEvent);

      // Then update enemy state.
      enemy.pathIdx++;
      enemy.lastPathTime = enemy.nextPathTime;
      enemy.nextPathTime += timeToDest;
    }
    // Update enemy position.
    float fracTraveled = (gameTime - enemy.lastPathTime) / (enemy.nextPathTime - enemy.lastPathTime);
    CppCellPos fromPos = enemy.path.get()[enemy.pathIdx - 1];
    CppCellPos toPos = enemy.path.get()[enemy.pathIdx];
    enemy.pos = (toPos - fromPos) * fracTraveled + fromPos;
  }
}

string CppBattleComputer::ComputeBattle(
    const vector<vector<int>>& towerIds,
    vector<int> wave,
    vector<vector<CppCellPos>> paths) {
  const int numRows = this->gameConfig.playfield.numRows;
  const int numCols = this->gameConfig.playfield.numCols;
  CppCellPos enemyEnter(
    this->gameConfig.playfield.enemyEnter / numRows,
    this->gameConfig.playfield.enemyEnter % numRows
  );
  cout << "Computing a " << numRows << " x " << numCols
    << " battle with " << wave.size() << " enemies and "
    << paths.size() << " paths." << endl;

  // Quick checks.
  assert(towerIds.size() == this->gameConfig.playfield.numRows);
  assert(towerIds[0].size() == this->gameConfig.playfield.numCols);
  assert(wave.size() == paths.size());

  // Output containers
  string errStr;
  vector<BattleEventFbT> events;
  float gameTime = -1.0;
  try {
    // Initialize tower states.
    vector<TowerState> towers = this->getInitialTowerStates(towerIds);

    // Store enemies in reverse order so we can efficiently remove from the end.
    vector<int> unspawnedEnemies(wave.crbegin(), wave.crend());

    // Main game loop
    uint16_t nextId = 0;
    uint16_t numSpawnedEnemies = 0;
    uint16_t ticks = -1; // This will be equal to 0 in the first loop.
    vector<EnemyState> spawnedEnemies;

    while (!unspawnedEnemies.empty() || !spawnedEnemies.empty()) {
      // Advance time
      ticks++;
      gameTime = ticks * this->gameTickSecs;

      // Per loop state
      vector<size_t> removedEnemyIdx;
      bool spawnOpen = true;
      if (!unspawnedEnemies.empty()) {
        for (const EnemyState &enemy : spawnedEnemies) {
          if (enemy.pos.distSq(enemyEnter) < 1.0) {
            spawnOpen = false;
            break;
          }
        }
      } else {
        // If there are no more enemies to spawn always mark the spawn as blocked.
        spawnOpen = false;
      }
      if (spawnOpen) {
        // Spawn new enemy
        int enemyConfigId = unspawnedEnemies.back();
        try {
          const EnemyConfig& enemyConfig = this->gameConfig.enemies.at(enemyConfigId);
          const vector<CppCellPos> &path = paths[numSpawnedEnemies];
          EnemyState newEnemy = EnemyState(nextId, path, gameTime, enemyConfig);
          numSpawnedEnemies++;
          nextId++;
          spawnedEnemies.push_back(newEnemy);

          // TODO: Update monsters spawned stats.
        }
        catch (const std::out_of_range& e) {
          stringstream ss;
          ss << "Could not find enemy config with ID: " << enemyConfigId;
          throw ss.str();
        }
        unspawnedEnemies.pop_back();
      }

      // Move spawned enemies
      MoveEnemies(gameTime, spawnedEnemies, events, removedEnemyIdx);

      // Remove any enemies marked for removal.
      // Do this in reverse order so we don't have to worry about indices changing as we remove enemies.
      for (auto enemyIdx = removedEnemyIdx.rbegin(); enemyIdx != removedEnemyIdx.rend(); enemyIdx++) {
        // Replace enemy at enemyIdx with the last element, then pop it.
        // This removes the enemy in constant time.
        assert(*enemyIdx >= 0);
        if (*enemyIdx != spawnedEnemies.size() - 1) {
          spawnedEnemies[*enemyIdx] = spawnedEnemies.back();
        }
        assert(!spawnedEnemies.empty());
        spawnedEnemies.pop_back();
      }
    }
  }
  catch (string err) {
    cerr << err << endl;
    errStr = err;
  }

  // First, serialize the events into a BattleEventsFb.
  flatbuffers::FlatBufferBuilder eventsBuilder(1024);
  vector<flatbuffers::Offset<BattleEventFb>> eventOffsets;
  // Sort events by start time.
  std::sort(events.begin(), events.end(), [](const BattleEventFbT &a, const BattleEventFbT &b) {
    return GetStartTime(a) < GetStartTime(b);
  });
  // Make offsets from events.
  for (const BattleEventFbT& event : events) {
    eventOffsets.push_back(CreateBattleEventFb(eventsBuilder, &event));
  }
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
  auto result = CreateBattleCalcResultsFb(builder, errStrOffset, monstersDefeatedFb, eventBytesFb, gameTime);
  builder.Finish(result);
  // Copy the created buffer into a std::string to pass to Python.
  string bytes((const char*)builder.GetBufferPointer(), builder.GetSize());
  return bytes;
}