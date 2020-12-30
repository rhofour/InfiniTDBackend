#include "cpp_battle_computer.h"

#include <algorithm>
#include <string>
#include <iostream>
#include <sstream>

#include "rapidjson/document.h"
#include "rapidjson/error/en.h"

using std::cout;
using std::cerr;
using std::endl;
using std::stringstream;
using std::pair;
using std::for_each;
using rapidjson::Document;
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

struct MonsterStats {
  uint16_t numSent;
  uint16_t numDefeated;

  MonsterStats(): numSent(0), numDefeated(0) {};
};

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

template<class T> void AddEvent(T &event, vector<BattleEventFbT> &events) {
  BattleEventFbT battleEvent;
  BattleEventUnionFbUnion battleEventUnion;
  battleEventUnion.Set(event);
  battleEvent.event = battleEventUnion;
  events.push_back(battleEvent);
}

void MoveEnemies(float gameTime, vector<EnemyState> &enemies, vector<BattleEventFbT> &events,
    vector<size_t> &removedEnemyIdx) {
  size_t enemyIdx = -1; // Intentional overflow so the first real value is 0.
  for (EnemyState &enemy : enemies) {
    enemyIdx++;
    if (enemy.nextPathTime <= gameTime) {
      // First, add remaining bit of path to distTraveled.
      enemy.distTraveled += enemy.pos.dist(enemy.path.get()[enemy.pathIdx]);

      assert(enemy.pathIdx < enemy.path.get().size());
      // Check if we've reached the destination.
      if (enemy.pathIdx == enemy.path.get().size() - 1) {
        // Remove this enemy.
        DeleteEventFbT deleteEvent;
        deleteEvent.obj_type = ObjectTypeFb::ObjectTypeFb_ENEMY;
        deleteEvent.id = enemy.id;
        deleteEvent.start_time = enemy.nextPathTime;
        AddEvent(deleteEvent, events);

        removedEnemyIdx.push_back(enemyIdx);
        // Mark the enemy as having no health so no towers try and fire on it.
        enemy.health = 0.0;
        continue;
      }
      // Otherwise make a new move event.
      MoveEventFbT moveEvent;
      moveEvent.obj_type = ObjectTypeFb::ObjectTypeFb_ENEMY;
      moveEvent.id = enemy.id;
      moveEvent.config_id = enemy.config.get().id;
      moveEvent.start_time = enemy.nextPathTime;
      const CppCellPos &prevDest = enemy.path.get()[enemy.pathIdx];
      moveEvent.start_pos = prevDest.toFp();
      const CppCellPos nextDest = enemy.path.get()[enemy.pathIdx + 1];
      float timeToDest = prevDest.dist(nextDest) / enemy.config.get().speed;
      moveEvent.dest_pos = nextDest.toFp();
      moveEvent.end_time = enemy.nextPathTime + timeToDest;
      AddEvent(moveEvent, events);

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

void UpdateTowers(float gameTime, vector<TowerState> &towers) {
  for (TowerState &tower : towers) {
    if (tower.config.firingRate <= 0) continue;
    float timeSinceAbleToFire = gameTime - (tower.lastFired + (1.0 / tower.config.firingRate));
    float firingRadius = std::clamp(
      timeSinceAbleToFire * tower.config.projectileSpeed, 0.0f, tower.config.range);
    tower.firingRadiusSq = firingRadius * firingRadius;
  }
}

// Note: These shots land at gameTime and were essentially fired in the past. This allows every
// shot to land exactly where the enemy will be.
void FireTowers(float gameTime, vector<TowerState> &towers, vector<EnemyState> &enemies,
    vector<BattleEventFbT> &events, vector<size_t> &removedEnemyIdx, uint16_t &nextId,
    unordered_map<uint16_t, MonsterStats> &monstersDefeated) {
  for (TowerState &tower : towers) {
    if (tower.firingRadiusSq == 0) continue;

    // Fire at the enemy which has traveled the farthest which we can reach.
    size_t enemyIdx = -1;
    float farthestEnemyDistSq = -1.0f;
    size_t farthestEnemyIdx;
    for (EnemyState &enemy : enemies) {
      enemyIdx++;
      float distSq = tower.pos.distSq(enemy.pos);
      if (distSq <= tower.firingRadiusSq && distSq > farthestEnemyDistSq && enemy.health > 0.0) {
        farthestEnemyDistSq = distSq;
        farthestEnemyIdx = enemyIdx;
      }
    }

    if (farthestEnemyDistSq > 0.0) {
      EnemyState &enemy = enemies[farthestEnemyIdx];
      // Update tower state.
      float shotDist = sqrt(farthestEnemyDistSq);
      float shotDuration = shotDist / tower.config.projectileSpeed;
      tower.lastFired = std::max(gameTime - shotDuration, 0.0f);

      // Create a projectile heading at the enemy.
      MoveEventFbT moveEvent;
      moveEvent.obj_type = ObjectTypeFb::ObjectTypeFb_PROJECTILE;
      moveEvent.id = nextId++;
      moveEvent.config_id = tower.config.projectileId;
      moveEvent.start_time = tower.lastFired;
      moveEvent.end_time = gameTime;
      moveEvent.start_pos = tower.pos.toFp();
      moveEvent.dest_pos = enemy.pos.toFp();
      AddEvent(moveEvent, events);
      DeleteEventFbT deleteProjEvent;
      deleteProjEvent.id = moveEvent.id;
      deleteProjEvent.obj_type = ObjectTypeFb::ObjectTypeFb_PROJECTILE;
      deleteProjEvent.start_time = gameTime;
      AddEvent(deleteProjEvent, events);

      // Update the enemy.
      enemy.health -= tower.config.damage;

      // Create a Damage event.
      DamageEventFbT damageEvent;
      damageEvent.id = enemy.id;
      damageEvent.health = enemy.health;
      damageEvent.start_time = gameTime;
      AddEvent(damageEvent, events);

      // Check if the enemy was defeated.
      if (enemy.health <= 0.0) {
        DeleteEventFbT deleteEnemyEvent;
        deleteEnemyEvent.id = enemy.id;
        deleteEnemyEvent.obj_type = ObjectTypeFb::ObjectTypeFb_ENEMY;
        deleteEnemyEvent.start_time = gameTime;
        AddEvent(deleteEnemyEvent, events);

        removedEnemyIdx.push_back(farthestEnemyIdx);
        monstersDefeated[enemy.config.get().id].numDefeated++;
      }
    }
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

  // Quick checks.
  assert(towerIds.size() == this->gameConfig.playfield.numRows);
  assert(towerIds[0].size() == this->gameConfig.playfield.numCols);
  assert(wave.size() == paths.size());

  // Output containers
  string errStr;
  vector<BattleEventFbT> events;
  unordered_map<uint16_t, MonsterStats> monstersDefeated;
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
          EnemyState newEnemy = EnemyState(nextId++, path, gameTime, enemyConfig);
          numSpawnedEnemies++;
          spawnedEnemies.push_back(newEnemy);

          monstersDefeated[enemyConfigId].numSent++;
        }
        catch (const std::out_of_range& e) {
          stringstream ss;
          ss << "Could not find enemy config with ID: " << enemyConfigId;
          throw ss.str();
        }
        unspawnedEnemies.pop_back();
      }

      MoveEnemies(gameTime, spawnedEnemies, events, removedEnemyIdx);

      UpdateTowers(gameTime, towers);

      FireTowers(gameTime, towers, spawnedEnemies, events, removedEnemyIdx, nextId, monstersDefeated);

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
  // Use stable sort so things like damage events arriving at the same time maintain their order.
  // Otherwise two damage events for the same enemy at the exact same time may be ordered so that the
  // event with the lower health comes first (and is effectively undone by the second event).
  std::stable_sort(events.begin(), events.end(), [](const BattleEventFbT &a, const BattleEventFbT &b) {
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
  for_each(monstersDefeated.cbegin(), monstersDefeated.cend(),
    [&monsterDefeatedFbs](pair<int16_t, MonsterStats> x) {
      monsterDefeatedFbs.push_back(MonsterDefeatedFb(x.first, x.second.numSent, x.second.numDefeated));
    });
  auto monstersDefeatedVector = builder.CreateVectorOfStructs(monsterDefeatedFbs);
  auto monstersDefeatedFb = CreateMonstersDefeatedFb(builder, monstersDefeatedVector);
  auto eventBytesFb = builder.CreateVector(eventsBuilder.GetBufferPointer(), eventsBuilder.GetSize());
  auto result = CreateBattleCalcResultsFb(builder, errStrOffset, monstersDefeatedFb, eventBytesFb, gameTime);
  builder.Finish(result);
  // Copy the created buffer into a std::string to pass to Python.
  string bytes((const char*)builder.GetBufferPointer(), builder.GetSize());
  return bytes;
}