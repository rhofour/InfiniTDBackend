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

class PlayfieldConfig {
 public:
  int numRows;
  int numCols;
  int enemyEnter;
  int enemyExit;

  PlayfieldConfig() {}
  PlayfieldConfig(const Value &val) {
    assert(val.IsObject());
    this->numRows = val["numRows"].GetInt();
    this->numCols = val["numCols"].GetInt();
    this->enemyEnter = val["monsterEnter"]["row"].GetInt() * numCols +
      val["monsterEnter"]["col"].GetInt();
    this->enemyExit = val["monsterExit"]["row"].GetInt() * numCols +
      val["monsterExit"]["col"].GetInt();
  }
};

class TowerConfig {
 public:
  float firingRate;
  float range;
  float damage;
  float projectileSpeed;
  int projectileId;

  TowerConfig(const Value& val) {
    assert(val.IsObject());
    this->firingRate = val["firingRate"].GetDouble();
    this->range = val["range"].GetDouble();
    this->damage = val["damage"].GetDouble();
    this->projectileSpeed = val["projectileSpeed"].GetDouble();
    this->projectileId = val["projectileId"].GetInt();
  }
};

class EnemyConfig {
 public:
  float health;
  float speed;
  float bounty;
  float size;

  EnemyConfig(const Value& val) {
    assert(val.IsObject());
    this->health = val["health"].GetDouble();
    this->speed = val["speed"].GetDouble();
    this->bounty = val["health"].GetDouble();
    this->size = val["health"].GetDouble();
  }
};

class GameConfig {
 public:
  PlayfieldConfig playfield;
  unordered_map<int, const TowerConfig> towers;
  unordered_map<int, const EnemyConfig> enemies;

  GameConfig() {}
  GameConfig(const Document& jsonDoc) {
    assert(jsonDoc.IsObject());
    assert(jsonDoc.HasMember("playfield"));
    this->playfield = PlayfieldConfig(jsonDoc["playfield"]);
    const Value& towers = jsonDoc["towers"];
    for (SizeType i = 0; i < towers.Size(); i++) {
      const int id = towers[i]["id"].GetInt();
      this->towers.insert({id, TowerConfig(towers[i])});
    }
    const Value& enemies = jsonDoc["monsters"];
    for (SizeType i = 0; i < enemies.Size(); i++) {
      const int id = enemies[i]["id"].GetInt();
      this->enemies.insert({id, EnemyConfig(enemies[i])});
    }
  }
};
