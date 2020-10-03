from dataclasses import dataclass
from typing import List, Set, Optional

from infinitdserver.game_config import CellPos, Row, Col
from infinitdserver.battleground_state import BattlegroundState

@dataclass(frozen=True)
class PathMap:
    dists: List[int]

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
    return distMap.dists[end.toNumber(numCols)] >= 0

def makeDistMap(battleground: BattlegroundState, start: CellPos, end: CellPos) -> PathMap:
    """makeDistMap calculates the distance of every point from the start, stopping if it finds the end.

    Used in makePathMap.
    """
    numCols = len(battleground.towers.towers[0])
    numRows = len(battleground.towers.towers)

    # distance from the start with -1 being unknown and -2 being impassable
    dists = [-1] * (numCols * numRows)
    i = 0
    for (row, rowTowers) in enumerate(battleground.towers.towers):
        for (col, tower) in enumerate(rowTowers):
            if tower is not None:
                dists[i] = -2
            i += 1

    startNumber = start.toNumber(numCols)
    if dists[startNumber] != -1:
        return PathMap(dists = dists)
    endNumber = end.toNumber(numCols)
    if dists[endNumber] != -1:
        return PathMap(dists = dists)

    def getNeighbors(elem: int) -> List[int]:
        col = elem % numCols
        row = elem // numCols
        neighbors = []
        if col > 0:
            neighbors.append(elem - 1)
        if col < numCols - 1:
            neighbors.append(elem + 1)
        if row > 0:
            neighbors.append(elem - numCols)
        if row < numRows - 1:
            neighbors.append(elem + numCols)
        return neighbors

    frontier = [startNumber]
    dist = 0
    dists[startNumber] = 0
    while dists[endNumber] == -1 and frontier:
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
    shortestPathLength = startDistMap.dists[end.toNumber(numCols)]
    if shortestPathLength < 0: # No path exists
        return None
    endDistMap = makeDistMap(battleground, end, start)
    assert shortestPathLength == endDistMap.dists[start.toNumber(numCols)]

    # Every element on a shortest path will have:
    # startDistMap[i] + endDistMap[i] == shortestPathLength
    dists = [-1] * (numCols * numRows)
    for i in range(numCols * numRows):
        if startDistMap.dists[i] + endDistMap.dists[i] == shortestPathLength:
            dists[i] = startDistMap.dists[i]
    return PathMap(dists = dists)

def findShortestPaths(battleground: BattlegroundState, start: CellPos, end: CellPos) -> List[List[CellPos]]:
    """Finds all of the shortest paths from start to end.

    This method infers the size of the battleground from it.
    """

    rows = len(battleground.towers.towers)
    cols = len(battleground.towers.towers[0])

    def neighbors(cell: CellPos) -> List[CellPos]:
        out = []
        if cell.row > 0:
            out.append(CellPos(cell.row - 1, cell.col))

        if cell.row < rows - 1:
            out.append(CellPos(cell.row + 1, cell.col))

        if cell.col > 0:
            out.append(CellPos(cell.row, cell.col - 1))

        if cell.col < cols - 1:
            out.append(CellPos(cell.row, cell.col + 1))
        return out

    # Turn the battleground into an occupancy map.
    occupiedOrSeen: Set[CellPos] = set()
    for (row, rowTowers) in enumerate(battleground.towers.towers):
        for (col, tower) in enumerate(rowTowers):
            if tower is not None:
                occupiedOrSeen.add(CellPos(row, col))

    if start in occupiedOrSeen:
        return []

    paths = [[start]]
    finalPaths = []
    while paths:
        newPaths = []
        newlySeen = set()
        for partialPath in paths:
            pathEnd = partialPath[-1]
            newlySeen.add(pathEnd)
            if pathEnd == end:
                finalPaths.append(partialPath)
                continue
            newNeighbors = [neighbor for neighbor in neighbors(pathEnd) if neighbor not in occupiedOrSeen]
            for neighbor in newNeighbors:
                newPaths.append(partialPath + [neighbor])

        if finalPaths:
            break # Skip the remaining steps if we already have the shortest paths
        paths = newPaths
        for new in newlySeen:
            occupiedOrSeen.add(new)

    return finalPaths
