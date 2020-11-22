#pragma once
#include <iostream>

class CppBattleComputer {
 public:
  CppBattleComputer() {};
  CppBattleComputer(std::string jsonText);
  void ComputeBattle(int seed);
};
