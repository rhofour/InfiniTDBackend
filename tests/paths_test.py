import unittest

from infinitdserver.game_config import CellPos
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.paths import makePathMap, findShortestPaths, compressPath, PathMap, pathExists

def emptyBattleground(rows: int, cols: int):
    return BattlegroundState(towers = BgTowersState([[None for c in range(cols)] for r in range(rows)]))

class TestPathExists(unittest.TestCase):
    def test_startBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][0] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(0, 0), CellPos(1, 1)))

    def test_endBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[1][1] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(0, 0), CellPos(1, 1)))

    def test_noPath(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][1] = BgTowerState(0)
        battleground.towers.towers[1][0] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(0, 0), CellPos(1, 1)))

    def test_oneStepPath(self):
        battleground = emptyBattleground(2, 2)

        self.assertTrue(pathExists(battleground, CellPos(0, 0), CellPos(1, 1)))

    def test_multiStepPath(self):
        battleground = emptyBattleground(2, 3)
        battleground.towers.towers[0][1] = BgTowerState(0)

        self.assertTrue(pathExists(battleground, CellPos(0, 0), CellPos(0, 2)))

    def test_multiplePaths(self):
        battleground = emptyBattleground(3, 3)
        battleground.towers.towers[1][1] = BgTowerState(0)

        self.assertTrue(pathExists(battleground, CellPos(0, 0), CellPos(2, 2)))

    def test_manyPaths(self):
        battleground = emptyBattleground(3, 3)

        self.assertTrue(pathExists(battleground, CellPos(0, 0), CellPos(2, 2)))

class TestMakePathMap(unittest.TestCase):
    def test_startBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][0] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertIsNone(pathMap)

    def test_endBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[1][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertIsNone(pathMap)

    def test_noPath(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][1] = BgTowerState(0)
        battleground.towers.towers[1][0] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(1, 1))

        self.assertIsNone(pathMap)

    def test_oneStepPath(self):
        battleground = emptyBattleground(2, 2)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(0, 1))

        expectedPathMap = PathMap(dists = [0, 1, -1, -1])
        self.assertEqual(pathMap, expectedPathMap)

    def test_multiStepPath(self):
        battleground = emptyBattleground(2, 3)
        battleground.towers.towers[0][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(0, 2))

        expectedPathMap = PathMap(dists = [0, -1, 4, 1, 2, 3])
        self.assertEqual(pathMap, expectedPathMap)

    def test_multiplePaths(self):
        battleground = emptyBattleground(3, 3)
        battleground.towers.towers[1][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(2, 2))

        expectedPathMap = PathMap(dists = [0, 1, 2, 1, -1, 3, 2, 3, 4])
        self.assertEqual(pathMap, expectedPathMap)

    def test_manyPaths(self):
        battleground = emptyBattleground(3, 3)

        pathMap = makePathMap(battleground, CellPos(0, 0), CellPos(2, 2))

        expectedPathMap = PathMap(dists = [0, 1, 2, 1, 2, 3, 2, 3, 4])
        self.assertEqual(pathMap, expectedPathMap)

class TestFindShortestPaths(unittest.TestCase):
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
        battleground.towers.towers[0][1] = BgTowerState(0)

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

class TestCompressPath(unittest.TestCase):
    def test_twoNodePaths(self):
        path1 = [CellPos(0, 0), CellPos(0, 1)]
        path2 = [CellPos(0, 0), CellPos(1, 0)]

        newPath1 = compressPath(path1)
        newPath2 = compressPath(path2)

        self.assertListEqual(newPath1, path1)
        self.assertListEqual(newPath2, path2)

    def test_singleChainPath(self):
        path1 = [CellPos(0, 0), CellPos(0, 1), CellPos(0, 2)]
        path2 = [CellPos(0, 0), CellPos(1, 0), CellPos(2, 0), CellPos(3, 0)]

        newPath1 = compressPath(path1)
        newPath2 = compressPath(path2)

        self.assertListEqual(newPath1, [CellPos(0, 0), CellPos(0, 2)])
        self.assertListEqual(newPath2, [CellPos(0, 0), CellPos(3, 0)])

    def test_twoCorners(self):
        path = [CellPos(0, 0), CellPos(0, 1), CellPos(0, 2), CellPos(1, 2), CellPos(1, 3)]

        newPath = compressPath(path)

        self.assertListEqual(newPath, [CellPos(0, 0), CellPos(0, 2), CellPos(1, 2), CellPos(1, 3)])
