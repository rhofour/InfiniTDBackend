import unittest
from typing import List, NewType
from enum import Enum, unique, auto

import attr
import cattr
from hypothesis import given
import hypothesis.strategies as st


from infinitdserver.game_config import GameConfig, CellPos, Row, Col, Url, MonsterConfig, ConfigId, TowerConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowerState
from infinitdserver.battle import Battle, BattleEvent, MoveEvent, DeleteEvent, ObjectType, EventType, FpCellPos, FpRow, FpCol, BattleResults
from infinitdserver.battle_computer import BattleComputer, MonsterState, TowerState, getShotTarget
from infinitdserver.game_config import ConfigId, CellPos, Row, Col
import test_data

class TestEnemyPosAtTime(unittest.TestCase):
    def setUp(self):
        self.enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(1.0), FpCol(0.0)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(2), Col(0)),
                CellPos(Row(2), Col(3)), CellPos(Row(3), Col(3)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = 0.5,
                bounty = 10.0,
                )
            )

    def test_sameTime(self):
        expected = self.enemy.pos

        res = self.enemy.posInFuture(0.0)

        self.assertEqual(res, expected)

    def test_noNewTarget(self):
        expected = FpCellPos(FpRow(1.5), FpCol(0.0))

        res = self.enemy.posInFuture(1.0)

        self.assertEqual(res, expected)

    def test_atTargetInPath(self):
        expected = FpCellPos(FpRow(2.0), FpCol(0.0))

        res = self.enemy.posInFuture(2.0)

        self.assertEqual(res, expected)

    def test_atNextTargetInPath(self):
        expected = FpCellPos(FpRow(2.0), FpCol(3.0))

        res = self.enemy.posInFuture(8.0)

        self.assertEqual(res, expected)

    def test_betweenFartherTargets(self):
        expected = FpCellPos(FpRow(2.5), FpCol(3.0))

        res = self.enemy.posInFuture(9.0)

        self.assertEqual(res, expected)

    def test_exactlyAtEnd(self):
        expected = FpCellPos(FpRow(3.0), FpCol(3.0))

        res = self.enemy.posInFuture(10.0)

        self.assertEqual(res, expected)

    def test_pastEnd(self):
        expected = None

        res = self.enemy.posInFuture(11.0)

        self.assertEqual(res, expected)

class TestEnemyTimeLeft(unittest.TestCase):
    @given(
            enemyStart=st.floats(0.0, 10.0),
            enemySpeed=st.floats(0.01, 50.0))
    def test_straightPath(self, enemyStart: float, enemySpeed: float):
        enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(0.0), FpCol(enemyStart)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(0), Col(10)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = enemySpeed,
                bounty = 10.0,
                )
            )

        res = enemy.timeLeft()

        self.assertEqual(res, (10 - enemyStart) / enemySpeed)

#class TestGetShotTarget(unittest.TestCase):
class GetShotTarget():
    @given(
            towerRow=st.integers(0, 10),
            towerCol=st.integers(0, 10),
            projectileSpeed=st.floats(0.01, 50.0),
            enemySpeed=st.floats(0.01, 50.0))
    def test_enemyWillBeAtTarget(self, towerRow: int, towerCol: int, projectileSpeed: float, enemySpeed: float):
        enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(0.0), FpCol(enemySpeed)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(0), Col(9)),
                CellPos(Row(9), Col(9)), CellPos(Row(9), Col(0)),
                CellPos(Row(0), Col(0)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = enemySpeed,
                bounty = 10.0,
                )
            )
        towerConfig = TowerConfig(
            id = ConfigId(0),
            url = Url("fake_url"),
            name = "Test Tower",
            cost = 1.0,
            firingRate = 2.0,
            range = 3.0,
            damage = 4.0,
            projectileSpeed = projectileSpeed,
            projectileId = ConfigId(0),
            )
        tower = TowerState(
            id = 0,
            config = towerConfig,
            pos = CellPos(Row(towerRow), Col(towerCol)),
            lastFired = -100.0,
        )

        res = getShotTarget(enemy, tower)
        if res:
            (target, timeToHit) = res
            timeToHit = target.dist(FpCellPos.fromCellPos(tower.pos)) / tower.config.projectileSpeed
            enemyPos = enemy.posInFuture(timeToHit)
            self.assertIsNotNone(enemyPos)
            dist = enemyPos.dist(target) # pytype: disable=attribute-error
            self.assertAlmostEqual(dist, 0.0, places=2)

    @given(
            projectileSpeed=st.floats(0.01, 50.0),
            enemySpeed=st.floats(0.01, 50.0))
    def test_shotWillNeverReachFasterEnemy(self, projectileSpeed: float, enemySpeed: float):
        enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(0.0), FpCol(enemySpeed)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(0), Col(9)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = projectileSpeed + enemySpeed, # Always > projectile speed
                bounty = 10.0,
                )
            )
        towerConfig = TowerConfig(
            id = ConfigId(0),
            url = Url("fake_url"),
            name = "Test Tower",
            cost = 1.0,
            firingRate = 2.0,
            range = 3.0,
            damage = 4.0,
            projectileSpeed = projectileSpeed,
            projectileId = ConfigId(0),
            )
        tower = TowerState(
            id = 0,
            config = towerConfig,
            pos = CellPos(Row(0), Col(0)),
            lastFired = -100.0,
        )

        res = getShotTarget(enemy, tower)
        self.assertIsNone(res)

    @given(
            projectileSpeed=st.floats(1.0, 50.0),
            enemySpeed=st.floats(0.01, 27.0))
    def test_shotWillAlwaysReachSlowerEnemy(self, projectileSpeed: float, enemySpeed: float):
        enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(0.0), FpCol(1.0)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(0), Col(9)),
                CellPos(Row(9), Col(9)), CellPos(Row(9), Col(0)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = enemySpeed,
                bounty = 10.0,
                )
            )
        towerConfig = TowerConfig(
            id = ConfigId(0),
            url = Url("fake_url"),
            name = "Test Tower",
            cost = 1.0,
            firingRate = 2.0,
            range = 3.0,
            damage = 4.0,
            projectileSpeed = projectileSpeed + enemySpeed, # Always > enemy speed
            projectileId = ConfigId(0),
            )
        tower = TowerState(
            id = 0,
            config = towerConfig,
            pos = CellPos(Row(0), Col(0)),
            lastFired = -100.0,
        )

        res = getShotTarget(enemy, tower)
        self.assertIsNotNone(res)

    @given(
            projectileSpeed=st.floats(0.01, 50.0),
            enemySpeed=st.floats(0.01, 50.0))
    def test_shotWillAlwaysReachOncomingEnemy(self, projectileSpeed: float, enemySpeed: float):
        enemy = MonsterState(
            id = ConfigId(0),
            pos = FpCellPos(FpRow(0.0), FpCol(1.0)),
            path = [
                CellPos(Row(0), Col(0)), CellPos(Row(0), Col(9)),
            ],
            health = 5.0,
            targetInPath = 1,
            config = MonsterConfig(
                id = ConfigId(0),
                url = Url("fake_url"),
                name = "Test Enemy",
                health = 5.0,
                speed = enemySpeed,
                bounty = 10.0,
                )
            )
        towerConfig = TowerConfig(
            id = ConfigId(0),
            url = Url("fake_url"),
            name = "Test Tower",
            cost = 1.0,
            firingRate = 2.0,
            range = 3.0,
            damage = 4.0,
            projectileSpeed = projectileSpeed,
            projectileId = ConfigId(0),
            )
        tower = TowerState(
            id = 0,
            config = towerConfig,
            pos = CellPos(Row(0), Col(9)),
            lastFired = -100.0,
        )

        res = getShotTarget(enemy, tower)
        self.assertIsNotNone(res)

class TestBattleComputerEvents(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_emptyWave(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)

        with self.assertRaises(ValueError) as context:
            results = battleComputer.computeBattle(battleground, [])

    def test_oneMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.0,
                endTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results.events, expectedEvents)

    def test_twoMonsterNoTowers(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig)
        battleground = BattlegroundState.empty(test_data.gameConfig)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.0,
                endTime = 1.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(0)),
                destPos = FpCellPos(FpRow(3), FpCol(0)),
                startTime = 0.5,
                endTime = 2.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 2.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(results.events, expectedEvents)

    def test_oneMonsterOneCorner(self):
        # Note which path the monster takes depends on the seed.
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(1), FpCol(0)),
                startTime = 0.0,
                endTime = 0.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(0)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results.events, expectedEvents)

    def test_oneMonsterOneCornerLowRes(self):
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col)
        lowResBattleComputer = BattleComputer(
                gameConfig = test_data.gameConfig2row2col, gameTickSecs = 0.2)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)

        results = battleComputer.computeBattle(battleground, [ConfigId(0)])
        lowResResults = lowResBattleComputer.computeBattle(battleground, [ConfigId(0)])

        self.assertListEqual(results.events, lowResResults.events)

    def test_twoMonstersOneCorner(self):
        # Note which path each monster takes depends on the seed.
        battleComputer = BattleComputer(gameConfig = test_data.gameConfig2row2col, seed=5)
        battleground = BattlegroundState.empty(test_data.gameConfig2row2col)
        expectedEvents: List[BattleEvent] = [
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(1)),
                startTime = 0.0,
                endTime = 0.5,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(0), FpCol(1)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(1)),
                destPos = FpCellPos(FpRow(1), FpCol(0)),
                startTime = 0.5,
                endTime = 1.0,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 0,
                startTime = 1.0,
            ),
            MoveEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                configId = ConfigId(0),
                startPos = FpCellPos(FpRow(1), FpCol(0)),
                destPos = FpCellPos(FpRow(0), FpCol(0)),
                startTime = 1.0,
                endTime = 1.5,
            ),
            DeleteEvent(
                objType = ObjectType.MONSTER,
                id = 1,
                startTime = 1.5,
            ),
        ]

        results = battleComputer.computeBattle(battleground, [ConfigId(0), ConfigId(0)])

        self.assertListEqual(results.events, expectedEvents)

class TestBattleEventEncodingAndDecoding(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_oneMoveEvent(self):
        battle = Battle(
            name = "testOneEvent",
            events = [
                MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    configId = ConfigId(0),
                    startPos = FpCellPos(FpRow(1), FpCol(0)),
                    destPos = FpCellPos(FpRow(0), FpCol(0)),
                    startTime = 1.0,
                    endTime = 1.5,
                ),
            ],
            results = BattleResults(
                monstersDefeated = {ConfigId(0): (0, 1)},
                bonuses = [],
                reward = 0.0,
                timeSecs = 1.5)
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)

    def test_twoEvents(self):
        battle = Battle(
            name = "testTwoEvents",
            events = [
                MoveEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    configId = ConfigId(0),
                    startPos = FpCellPos(FpRow(1), FpCol(0)),
                    destPos = FpCellPos(FpRow(0), FpCol(0)),
                    startTime = 1.0,
                    endTime = 1.5,
                ),
                DeleteEvent(
                    objType = ObjectType.MONSTER,
                    id = 1,
                    startTime = 1.5,
                ),
            ],
            results = BattleResults(
                monstersDefeated = {ConfigId(0): (0, 1)},
                bonuses = [],
                reward = 0.0,
                timeSecs = 1.5)
        )

        encodedStr = battle.encodeEvents()
        decodedEvents = Battle.decodeEvents(encodedStr)

        self.assertEqual(battle.events, decodedEvents)
