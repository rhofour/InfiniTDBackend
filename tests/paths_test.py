import unittest
from random import Random

import numpy as np

from infinitd_server.game_config import CellPos, Row, Col
from infinitd_server.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitd_server.paths import makePathMap, compressPath, PathMap, pathExists

def emptyBattleground(rows: int, cols: int):
    return BattlegroundState(towers = BgTowersState([[None for c in range(cols)] for r in range(rows)]))

class TestGetRandomPath(unittest.TestCase):
    def test_diagonal2(self):
        battleground = emptyBattleground(2, 2)
        start = CellPos(Row(0), Col(0))
        end = CellPos(Row(1), Col(1))
        pathMap = makePathMap(battleground, start, end)
        self.assertIsNotNone(pathMap)

        for i in range(10):
            with self.subTest(seed=i):
                path = pathMap.getRandomPath(
                        start, Random(i)) # pytype: disable=attribute-error
                self.assertEqual(len(path), 3)
                self.assertEqual(path[0], start)
                self.assertEqual(path[-1], end)
                # Make sure each position is adjacent to the previous
                prevElem = path[0]
                for elem in path[1:]:
                    self.assertGreaterEqual(elem.row, prevElem.row - 1)
                    self.assertLessEqual(elem.row, prevElem.row + 1)
                    self.assertGreaterEqual(elem.col, prevElem.col - 1)
                    self.assertLessEqual(elem.col, prevElem.col + 1)
                    prevElem = elem

    def test_diagonal5(self):
        battleground = emptyBattleground(5, 5)
        start = CellPos(Row(0), Col(0))
        end = CellPos(Row(4), Col(4))
        pathMap = makePathMap(battleground, start, end)
        self.assertIsNotNone(pathMap)

        for i in range(10):
            with self.subTest(seed=i):
                path = pathMap.getRandomPath(
                        start, Random(i)) # pytype: disable=attribute-error
                self.assertEqual(len(path), 9)
                self.assertEqual(path[0], start)
                self.assertEqual(path[-1], end)
                # Make sure each position is adjacent to the previous
                prevElem = path[0]
                for elem in path[1:]:
                    self.assertGreaterEqual(elem.row, prevElem.row - 1)
                    self.assertLessEqual(elem.row, prevElem.row + 1)
                    self.assertGreaterEqual(elem.col, prevElem.col - 1)
                    self.assertLessEqual(elem.col, prevElem.col + 1)
                    prevElem = elem

    def test_diagonal5_with_obstacles(self):
        battleground = emptyBattleground(5, 5)
        battleground.towers.towers[2][2] = BgTowerState(0)
        battleground.towers.towers[2][3] = BgTowerState(0)
        battleground.towers.towers[3][2] = BgTowerState(0)
        battleground.towers.towers[3][3] = BgTowerState(0)
        start = CellPos(Row(0), Col(0))
        end = CellPos(Row(4), Col(4))
        pathMap = makePathMap(battleground, start, end)
        self.assertIsNotNone(pathMap)

        for i in range(10):
            with self.subTest(seed=i):
                path = pathMap.getRandomPath(
                        start, Random(i)) # pytype: disable=attribute-error
                self.assertEqual(len(path), 9)
                self.assertEqual(path[0], start)
                self.assertEqual(path[-1], end)
                # Make sure each position is adjacent to the previous
                prevElem = path[0]
                for elem in path[1:]:
                    self.assertGreaterEqual(elem.row, prevElem.row - 1)
                    self.assertLessEqual(elem.row, prevElem.row + 1)
                    self.assertGreaterEqual(elem.col, prevElem.col - 1)
                    self.assertLessEqual(elem.col, prevElem.col + 1)
                    prevElem = elem

class TestPathExists(unittest.TestCase):
    def test_startBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][0] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1))))

    def test_endBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[1][1] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1))))

    def test_noPath(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][1] = BgTowerState(0)
        battleground.towers.towers[1][0] = BgTowerState(0)

        self.assertFalse(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1))))

    def test_oneStepPath(self):
        battleground = emptyBattleground(2, 2)

        self.assertTrue(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1))))

    def test_multiStepPath(self):
        battleground = emptyBattleground(2, 3)
        battleground.towers.towers[0][1] = BgTowerState(0)

        self.assertTrue(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(0), Col(2))))

    def test_multiplePaths(self):
        battleground = emptyBattleground(3, 3)
        battleground.towers.towers[1][1] = BgTowerState(0)

        self.assertTrue(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(2), Col(2))))

    def test_manyPaths(self):
        battleground = emptyBattleground(3, 3)

        self.assertTrue(pathExists(battleground, CellPos(Row(0), Col(0)), CellPos(Row(2), Col(2))))

class TestMakePathMap(unittest.TestCase):
    def test_startBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][0] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1)))

        self.assertIsNone(pathMap)

    def test_endBlocked(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[1][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1)))

        self.assertIsNone(pathMap)

    def test_noPath(self):
        battleground = emptyBattleground(2, 2)
        battleground.towers.towers[0][1] = BgTowerState(0)
        battleground.towers.towers[1][0] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(1), Col(1)))

        self.assertIsNone(pathMap)

    def test_oneStepPath(self):
        battleground = emptyBattleground(2, 2)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(0), Col(1)))

        np.testing.assert_array_equal(
            pathMap.dists, np.asarray([[0, 1], [-1, -1]]))

    def test_multiStepPath(self):
        battleground = emptyBattleground(2, 3)
        battleground.towers.towers[0][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(0), Col(2)))

        np.testing.assert_array_equal(
            pathMap.dists, np.asarray([[0, -1, 4], [1, 2, 3]]))

    def test_multiplePaths(self):
        battleground = emptyBattleground(3, 3)
        battleground.towers.towers[1][1] = BgTowerState(0)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(2), Col(2)))

        np.testing.assert_array_equal(pathMap.dists,
            np.asarray([[0, 1, 2], [1, -1, 3], [2, 3, 4]]))

    def test_manyPaths(self):
        battleground = emptyBattleground(3, 3)

        pathMap = makePathMap(battleground, CellPos(Row(0), Col(0)), CellPos(Row(2), Col(2)))

        np.testing.assert_array_equal(
            pathMap.dists, np.asarray([[0, 1, 2], [1, 2, 3], [2, 3, 4]]))

class TestCompressPath(unittest.TestCase):
    def test_twoNodePaths(self):
        path1 = [CellPos(Row(0), Col(0)), CellPos(Row(0), Col(1))]
        path2 = [CellPos(Row(0), Col(0)), CellPos(Row(1), Col(0))]

        newPath1 = compressPath(path1)
        newPath2 = compressPath(path2)

        self.assertListEqual(newPath1, path1)
        self.assertListEqual(newPath2, path2)

    def test_singleChainPath(self):
        path1 = [CellPos(Row(0), Col(0)), CellPos(Row(0), Col(1)), CellPos(Row(0), Col(2))]
        path2 = [CellPos(Row(0), Col(0)), CellPos(Row(1), Col(0)), CellPos(Row(2), Col(0)),
                CellPos(Row(3), Col(0))]

        newPath1 = compressPath(path1)
        newPath2 = compressPath(path2)

        self.assertListEqual(newPath1, [CellPos(Row(0), Col(0)), CellPos(Row(0), Col(2))])
        self.assertListEqual(newPath2, [CellPos(Row(0), Col(0)), CellPos(Row(3), Col(0))])

    def test_twoCorners(self):
        path = [CellPos(Row(0), Col(0)), CellPos(Row(0), Col(1)), CellPos(Row(0), Col(2)),
                CellPos(Row(1), Col(2)), CellPos(Row(1), Col(3))]

        newPath = compressPath(path)

        self.assertListEqual(newPath,
                [CellPos(Row(0), Col(0)), CellPos(Row(0), Col(2)), CellPos(Row(1), Col(2)),
                    CellPos(Row(1), Col(3))])
