#pragma once
#include <iostream>
#include <unordered_map>

#include "rapidjson/document.h"

using std::cout;
using std::endl;
using std::unordered_map;
using rapidjson::Document;
using rapidjson::Value;
using rapidjson::SizeType;

double GetDoubleOrDie(const Value& val, const char* fieldName) {
  Value::ConstMemberIterator itr = val.FindMember(fieldName);
  assert(itr != val.MemberEnd());
  assert(itr->value.IsDouble());
  return itr->value.GetDouble();
}

int GetIntOrDie(const Value& val, const char* fieldName) {
  Value::ConstMemberIterator itr = val.FindMember(fieldName);
  assert(itr != val.MemberEnd());
  assert(itr->value.IsInt());
  return itr->value.GetInt();
}

uint16_t GetUintOrDie(const Value& val, const char* fieldName) {
  Value::ConstMemberIterator itr = val.FindMember(fieldName);
  assert(itr != val.MemberEnd());
  assert(itr->value.IsUint());
  return itr->value.GetUint();
}

class PlayfieldConfig {
 public:
  int numRows;
  int numCols;
  int enemyEnter;
  int enemyExit;

  PlayfieldConfig() {}
  PlayfieldConfig(const Value &val) {
    assert(val.IsObject());
    this->numRows = GetIntOrDie(val, "numRows");
    this->numCols = GetIntOrDie(val, "numCols");
    this->enemyEnter = GetIntOrDie(val["monsterEnter"], "row") * numCols +
      GetIntOrDie(val["monsterEnter"], "col");
    this->enemyExit = GetIntOrDie(val["monsterExit"], "row") * numCols +
      GetIntOrDie(val["monsterExit"], "col");
  }
};

class TowerConfig {
 public:
  float firingRate;
  float range;
  float damage;
  float projectileSpeed;
  uint16_t id;

  TowerConfig(const Value& val) {
    assert(val.IsObject());
    this->firingRate = GetDoubleOrDie(val, "firingRate");
    this->range = GetDoubleOrDie(val, "range");
    this->damage = GetDoubleOrDie(val, "damage");
    this->projectileSpeed = GetDoubleOrDie(val, "projectileSpeed");
    this->id = GetUintOrDie(val, "id");
  }
};

class EnemyConfig {
 public:
  float health;
  float speed;
  float bounty;
  float size;
  uint16_t id;

  EnemyConfig(const Value& val) {
    assert(val.IsObject());
    this->health = GetDoubleOrDie(val, "health");
    this->speed = GetDoubleOrDie(val, "speed");
    this->bounty = GetDoubleOrDie(val, "bounty");
    this->id = GetUintOrDie(val, "id");
  }
};

class GameConfig {
 public:
  PlayfieldConfig playfield;
  unordered_map<uint16_t, const TowerConfig> towers;
  unordered_map<uint16_t, const EnemyConfig> enemies;

  GameConfig() {}
  GameConfig(const Document& jsonDoc) {
    assert(jsonDoc.IsObject());
    assert(jsonDoc.HasMember("playfield"));
    this->playfield = PlayfieldConfig(jsonDoc["playfield"]);
    const Value& towers = jsonDoc["towers"];
    for (SizeType i = 0; i < towers.Size(); i++) {
      const uint16_t id = GetUintOrDie(towers[i], "id");
      this->towers.insert({id, TowerConfig(towers[i])});
    }
    const Value& enemies = jsonDoc["monsters"];
    for (SizeType i = 0; i < enemies.Size(); i++) {
      const uint16_t id = GetUintOrDie(enemies[i], "id");
      this->enemies.insert({id, EnemyConfig(enemies[i])});
    }
  }
};
