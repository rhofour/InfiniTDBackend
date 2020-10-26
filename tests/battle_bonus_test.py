import unittest

from infinitdserver.game_config import BonusType, BonusCondition, BattleBonus, ConfigId

class TestBattleBonus(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_additiveBonus(self):
        additiveBonus = BattleBonus(
                id = ConfigId(0),
                name = "additive bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [])

        self.assertEqual(additiveBonus.getAmount(15.0), 10.0)

    def test_multiplicativeBonus(self):
        multiplicativeBonus = BattleBonus(
                id = ConfigId(0),
                name = "multiplicative bonus",
                bonusType = BonusType.MULTIPLICATIVE,
                bonusAmount = 1.5,
                conditions = [])

        self.assertEqual(multiplicativeBonus.getAmount(10.0), 5.0)

    def test_noConditionsIsAlwaysEarned(self):
        additiveBonus = BattleBonus(
                id = ConfigId(0),
                name = "additive bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [])
        emptyResults = {}
        noDefeatResults = {ConfigId(0): (0,5), ConfigId(1): (0, 3)}
        mixedResults = {ConfigId(0): (2, 5), ConfigId(1): (1, 3)}
        perfectResults = {ConfigId(0): (5, 5), ConfigId(1): (3, 3)}

        self.assertTrue(additiveBonus.isEarned(emptyResults))
        self.assertTrue(additiveBonus.isEarned(noDefeatResults))
        self.assertTrue(additiveBonus.isEarned(mixedResults))
        self.assertTrue(additiveBonus.isEarned(perfectResults))

    def test_zeroPercentDefeatedCondition(self):
        bonus = BattleBonus(
                id = ConfigId(0),
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 0.0)])
        emptyResults = {}
        noDefeatResults = {ConfigId(0): (0,5), ConfigId(1): (0, 3)}
        mixedResults = {ConfigId(0): (2, 5), ConfigId(1): (1, 3)}
        perfectResults = {ConfigId(0): (5, 5), ConfigId(1): (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertTrue(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_fiftyPercentDefeatedCondition(self):
        bonus = BattleBonus(
                id = ConfigId(0),
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 50.0)])
        emptyResults = {}
        noDefeatResults = {ConfigId(0): (0,5), ConfigId(1): (0, 3)}
        mixedResults = {ConfigId(0): (3, 5), ConfigId(1): (2, 4)}
        perfectResults = {ConfigId(0): (5, 5), ConfigId(1): (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_oneHundredPercentDefeatedCondition(self):
        bonus = BattleBonus(
                id = ConfigId(0),
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 100.0)])
        emptyResults = {}
        noDefeatResults = {ConfigId(0): (0,5), ConfigId(1): (0, 3)}
        mixedResults = {ConfigId(0): (3, 5), ConfigId(1): (2, 4)}
        perfectResults = {ConfigId(0): (5, 5), ConfigId(1): (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertFalse(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_multiplePercentDefeatedConditions(self):
        bonus = BattleBonus(
                id = ConfigId(0),
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [
                    BonusCondition(percentDefeated = 10.0),
                    BonusCondition(percentDefeated = 50.0)])
        emptyResults = {}
        noDefeatResults = {ConfigId(0): (0,5), ConfigId(1): (0, 3)}
        mixedResults = {ConfigId(0): (3, 5), ConfigId(1): (2, 4)}
        perfectResults = {ConfigId(0): (5, 5), ConfigId(1): (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))
