#include "cpp_battle_computer.h"

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
  cout << "Got JSON: " << jsonText << endl;
}

void CppBattleComputer::ComputeBattle(int seed) {
  cout << "Computing a battle with seed: " << seed << endl;
}
