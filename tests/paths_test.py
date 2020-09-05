import unittest

from infinitdserver.game_config import CellPos
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.paths import findShortestPaths

def emptyBattleground(rows: int, cols: int):
    return BattlegroundState(towers = BgTowersState([[None for c in range(cols)] for r in range(rows)]))

class TestPaths(unittest.TestCase):
    def test_startBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][0] = BgTowerState(0)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertCountEqual(paths, [])

    def test_endBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[1][1] = BgTowerState(0)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertCountEqual(paths, [])

    def test_noPath(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][1] = BgTowerState(0)
        battleground.towers.towers[1][0] = BgTowerState(0)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertCountEqual(paths, [])

    def test_oneStepPath(self):
        battleground = emptyBattleground(2, 2)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(0, 1))

        self.assertCountEqual(paths, [[CellPos(0, 0), CellPos(0, 1)]])

    def test_multiStepPath(self):
        battleground = emptyBattleground(2, 3)
        print(battleground)
        battleground.towers.towers[0][1] = BgTowerState(0)
        print(battleground)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(0, 2))

        self.assertCountEqual(paths, [[CellPos(0, 0), CellPos(1, 0), CellPos(1, 1), CellPos(1, 2), CellPos(0, 2)]])

    def test_multiplePaths(self):
        battleground = emptyBattleground(3, 3)
        battleground.towers.towers[1][1] = BgTowerState(0)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(2, 2))

        self.assertCountEqual(paths, [
            [CellPos(0, 0), CellPos(1, 0), CellPos(2, 0), CellPos(2, 1), CellPos(2, 2)],
            [CellPos(0, 0), CellPos(0, 1), CellPos(0, 2), CellPos(1, 2), CellPos(2, 2)],
            ])

    def test_manyPaths(self):
        battleground = emptyBattleground(3, 3)

        paths = findShortestPaths(battleground, CellPos(0, 0), CellPos(2, 2))

        self.assertEqual(len(paths), 6)
