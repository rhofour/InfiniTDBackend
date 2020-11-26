from dataclasses import dataclass
from random import Random
from typing import List, Set, Optional, Tuple

import numpy as np

from infinitd_server.game_config import CellPos, Row, Col
from infinitd_server.battleground_state import BattlegroundState

@dataclass(frozen=True)
class PathMap:
    dists: np.ndarray

    def getRandomPath(self, start: CellPos,
            rand: Optional[Random] = None) -> List[CellPos]:
        if rand is None:
            rand = Random()
        numRows, numCols = self.dists.shape
        def getNeighbors(elem: Tuple[int, int]) -> List[Tuple[int, int]]:
            row, col = elem
            neighbors = []
            if col > 0:
                neighbors.append((row, col - 1))
            if col < numCols - 1:
                neighbors.append((row, col + 1))
            if row > 0:
                neighbors.append((row - 1, col))
            if row < numRows - 1:
                neighbors.append((row + 1, col))
            return neighbors

        path = []
        currentDist = -1
        possibleNeighbors = [start.toTuple()]
        while possibleNeighbors:
            currentPos = rand.choice(possibleNeighbors)
            path.append(CellPos.fromTuple(currentPos))
            currentDist += 1
            possibleNeighbors = [neighbor
                    for neighbor in getNeighbors(currentPos)
                    if self.dists[neighbor] == currentDist + 1]
        if len(path) < 2:
            raise Exception(f"Path has length {len(path)} from PathMap: {self.readableStr(numCols)}")
        return path

def compressPath(path: List[CellPos]) -> List[CellPos]:
    if len(path) < 2:
        raise ValueError("A valid path must have at least two nodes.")
    newPath = [path[0]]
    movingHorizontally = path[1].row == path[0].row
    for node in path[2:]:
        if movingHorizontally and node.row != newPath[-1].row:
            movingHorizontally = False
            newPath.append(CellPos(Row(newPath[-1].row), node.col))
        elif not movingHorizontally and node.col != newPath[-1].col:
            movingHorizontally = True
            newPath.append(CellPos(node.row, Col(newPath[-1].col)))
    newPath.append(path[-1])
    return newPath

def pathExists(battleground: BattlegroundState, start: CellPos, end: CellPos) -> bool:
    # This would likely be faster if implemented as A* instead.
    numCols = len(battleground.towers.towers[0])
    distMap = makeDistMap(battleground, start, end)
    return distMap.dists[end.toTuple()] >= 0

def makeDistMap(battleground: BattlegroundState, start: CellPos, end: CellPos) -> PathMap:
    """makeDistMap calculates the distance of every point from the start, stopping if it finds the end.

    Used in makePathMap.
    """
    numCols = len(battleground.towers.towers[0])
    numRows = len(battleground.towers.towers)

    # distance from the start with -1 being unknown and -2 being impassable
    dists = np.full((numRows, numCols), -1)
    for (row, rowTowers) in enumerate(battleground.towers.towers):
        for (col, tower) in enumerate(rowTowers):
            if tower is not None:
                dists[row, col] = -2

    startTuple = start.toTuple()
    if dists[startTuple] != -1:
        return PathMap(dists = dists)
    endTuple = end.toTuple()
    if dists[endTuple] != -1:
        return PathMap(dists = dists)

    def getNeighbors(elem: Tuple[int, int]) -> List[Tuple[int, int]]:
        row, col = elem
        neighbors = []
        if col > 0:
            neighbors.append((row, col - 1))
        if col < numCols - 1:
            neighbors.append((row, col + 1))
        if row > 0:
            neighbors.append((row - 1, col))
        if row < numRows - 1:
            neighbors.append((row + 1, col))
        return neighbors

    frontier = [startTuple]
    dist = 0
    dists[startTuple] = 0
    while dists[endTuple] == -1 and frontier:
        nextFrontier = []
        for frontierElem in frontier:
            assert dists[frontierElem] == dist
            for neighbor in getNeighbors(frontierElem):
                if dists[neighbor] == -1:
                    dists[neighbor] = dist + 1
                    nextFrontier.append(neighbor)

        dist += 1
        frontier = nextFrontier

    return PathMap(dists = dists)

def makePathMap(battleground: BattlegroundState, start: CellPos, end: CellPos) -> Optional[PathMap]:
    numCols = len(battleground.towers.towers[0])
    numRows = len(battleground.towers.towers)

    startDistMap = makeDistMap(battleground, start, end)
    shortestPathLength = startDistMap.dists[end.toTuple()]
    if shortestPathLength < 0: # No path exists
        return None
    endDistMap = makeDistMap(battleground, end, start)
    assert shortestPathLength == endDistMap.dists[start.toTuple()]

    # Every element on a shortest path will have:
    # startDistMap[i] + endDistMap[i] == shortestPathLength
    dists = np.where(
            startDistMap.dists + endDistMap.dists == shortestPathLength,
            startDistMap.dists, -1)
    return PathMap(dists = dists)
