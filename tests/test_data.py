from infinitdserver.game_config import *

playfieldConfig6row3col = PlayfieldConfig(
    numRows = 6,
    numCols = 3,
    monsterEnter = CellPos(Row(0), Col(0)),
    monsterExit = CellPos(Row(5), Col(0)),
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
        id = ConfigId(0),
        url = Url(""),
        name = "Cheap Tower",
        cost = 1,
        firingRate = 0.5,
        range = 2.0,
        damage = 5.0,
        projectileSpeed = 2.0,
        projectileId = ConfigId(0),
        ),
    TowerConfig(
        id = ConfigId(1),
        url = Url(""),
        name = "Expensive Tower",
        cost = 101,
        firingRate = 1.0,
        range = 2.0,
        damage = 15.0,
        projectileSpeed = 2.0,
        projectileId = ConfigId(0),
        ),
    TowerConfig(
        id = ConfigId(2),
        url = Url(""),
        name = "Fence",
        cost = 2,
        firingRate = 0.0,
        range = 10.0,
        damage = 5.0,
        projectileSpeed = 1.5,
        projectileId = ConfigId(0),
        ),
    ]

projectiles = [
    ProjectileConfig(
        id = ConfigId(0),
        url = Url(""),
        size = 16),
    ]

monsters = [
        MonsterConfig(
            id = ConfigId(0),
            url = Url(""),
            name = "Test Enemy 0",
            health = 10.0,
            speed = 2.0,
            bounty = 10.0),
        MonsterConfig(
            id = ConfigId(1),
            url = Url(""),
            name = "Test Enemy 1",
            health = 8.0,
            speed = 3.5,
            bounty = 20.0),
    ]

battleBonuses = [
        BattleBonus(
            id = ConfigId(0),
            name = "Participation",
            bonusType = BonusType.ADDITIVE,
            bonusAmount = 1,
            conditions = [ BonusCondition(percentDefeated = 0.0) ],
        ),
    ]

gameConfigData = GameConfigData(
    playfield = playfieldConfig6row3col,
    tiles = [],
    towers = towers,
    projectiles = projectiles,
    monsters = monsters,
    misc = MiscConfigData(
        sellMultiplier = 0.5,
        startingGold = 100,
        minGoldPerMinute = 1.0,
        battleBonuses = battleBonuses,
    ))

gameConfig2row2colData = GameConfigData(
    playfield = playfieldConfig2row2col,
    tiles = [],
    towers = towers,
    projectiles = projectiles,
    monsters = monsters,
    misc = MiscConfigData(
        sellMultiplier = 0.5,
        startingGold = 100,
        minGoldPerMinute = 1.0,
        battleBonuses = battleBonuses,
    ))

gameConfig = GameConfig.fromGameConfigData(gameConfigData)
gameConfig2row2col = GameConfig.fromGameConfigData(gameConfig2row2colData)
