from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig, MiscConfig

playfieldConfig = PlayfieldConfig(
    numRows = 4,
    numCols = 3,
    monsterEnter = CellPos(Row(0), Col(0)),
    monsterExit = CellPos(Row(3), Col(2)),
    backgroundId = 0,
    pathId = 0,
    pathStartId = 0,
    pathEndId = 0,
    )
towers = [
    TowerConfig(
        id = 0,
        url = "",
        name = "Cheap Tower",
        cost = 1,
        firingRate = 1.0,
        range = 10.0,
        damage = 5.0),
    TowerConfig(
        id = 1,
        url = "",
        name = "Expensive Tower",
        cost = 101,
        firingRate = 1.0,
        range = 10.0,
        damage = 5.0),
    TowerConfig(
        id = 2,
        url = "",
        name = "Other Tower",
        cost = 2,
        firingRate = 1.0,
        range = 10.0,
        damage = 5.0),
    ]
gameConfig = GameConfig(
    playfield = playfieldConfig,
    tiles = (),
    towers = towers,
    monsters = (),
    misc = MiscConfig(
        sellMultiplier = 0.5,
        startingGold = 100,
        minGoldPerMinute = 1.0
    ))
