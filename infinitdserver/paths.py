from typing import List, Tuple, Set

from infinitdserver.game_config import CellPos
from infinitdserver.battleground_state import BattlegroundState

def findShortestPaths(battleground: BattlegroundState, start: CellPos, end: CellPos) -> List[List[Tuple[int, int]]]:
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
