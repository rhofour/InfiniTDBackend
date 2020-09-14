from infinitdserver.game_config import PlayfieldConfig, CellPos, Row, Col, TowerConfig, GameConfig, MiscConfig, MonsterConfig

playfieldConfig4row3col = PlayfieldConfig(
    numRows = 4,
    numCols = 3,
    monsterEnter = CellPos(Row(0), Col(0)),
    monsterExit = CellPos(Row(3), Col(0)),
    backgroundId = 0,
    pathId = 0,
    pathStartId = 0,
    pathEndId = 0,
    )

playfieldConfig2row2col = PlayfieldConfig(
    numRows = 2,
    numCols = 2,
    monsterEnter = CellPos(Row(1), Col(1)),
    monsterExit = CellPos(Row(0), Col(0)),
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

monsters = [
        MonsterConfig(
            id = 0,
            url = "",
            name = "Test Enemy 0",
            health = 5.0,
            speed = 2.0,
            bounty = 10.0),
        MonsterConfig(
            id = 1,
            url = "",
            name = "Test Enemy 1",
            health = 8.0,
            speed = 3.5,
            bounty = 20.0),
    ]

gameConfig = GameConfig(
    playfield = playfieldConfig4row3col,
    tiles = (),
    towers = towers,
    monsters = monsters,
    misc = MiscConfig(
        sellMultiplier = 0.5,
        startingGold = 100,
        minGoldPerMinute = 1.0,
        fullWaveMultiplier = 3.0,
    ))

gameConfig2row2col = GameConfig(
    playfield = playfieldConfig2row2col,
    tiles = (),
    towers = towers,
    monsters = monsters,
    misc = MiscConfig(
        sellMultiplier = 0.5,
        startingGold = 100,
        minGoldPerMinute = 1.0,
        fullWaveMultiplier = 3.0,
    ))
