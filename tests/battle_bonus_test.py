import unittest

from infinitdserver.game_config import BonusType, BonusCondition, BattleBonus

class TestBattleBonus(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_additiveBonus(self):
        additiveBonus = BattleBonus(
                name = "additive bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [])

        self.assertEqual(additiveBonus.getAmount(15.0), 10.0)

    def test_multiplicativeBonus(self):
        multiplicativeBonus = BattleBonus(
                name = "multiplicative bonus",
                bonusType = BonusType.MULTIPLICATIVE,
                bonusAmount = 1.5,
                conditions = [])

        self.assertEqual(multiplicativeBonus.getAmount(10.0), 5.0)

    def test_noConditionsIsAlwaysEarned(self):
        additiveBonus = BattleBonus(
                name = "additive bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [])
        emptyResults = {}
        noDefeatResults = {0: (0,5), 1: (0, 3)}
        mixedResults = {0: (2, 5), 1: (1, 3)}
        perfectResults = {0: (5, 5), 1: (3, 3)}

        self.assertTrue(additiveBonus.isEarned(emptyResults))
        self.assertTrue(additiveBonus.isEarned(noDefeatResults))
        self.assertTrue(additiveBonus.isEarned(mixedResults))
        self.assertTrue(additiveBonus.isEarned(perfectResults))

    def test_zeroPercentDefeatedCondition(self):
        bonus = BattleBonus(
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 0.0)])
        emptyResults = {}
        noDefeatResults = {0: (0,5), 1: (0, 3)}
        mixedResults = {0: (2, 5), 1: (1, 3)}
        perfectResults = {0: (5, 5), 1: (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertTrue(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_fiftyPercentDefeatedCondition(self):
        bonus = BattleBonus(
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 50.0)])
        emptyResults = {}
        noDefeatResults = {0: (0,5), 1: (0, 3)}
        mixedResults = {0: (3, 5), 1: (2, 4)}
        perfectResults = {0: (5, 5), 1: (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_oneHundredPercentDefeatedCondition(self):
        bonus = BattleBonus(
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [BonusCondition(percentDefeated = 100.0)])
        emptyResults = {}
        noDefeatResults = {0: (0,5), 1: (0, 3)}
        mixedResults = {0: (3, 5), 1: (2, 4)}
        perfectResults = {0: (5, 5), 1: (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertFalse(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))

    def test_multiplePercentDefeatedConditions(self):
        bonus = BattleBonus(
                name = "test bonus",
                bonusType = BonusType.ADDITIVE,
                bonusAmount = 10.0,
                conditions = [
                    BonusCondition(percentDefeated = 10.0),
                    BonusCondition(percentDefeated = 50.0)])
        emptyResults = {}
        noDefeatResults = {0: (0,5), 1: (0, 3)}
        mixedResults = {0: (3, 5), 1: (2, 4)}
        perfectResults = {0: (5, 5), 1: (3, 3)}

        self.assertFalse(bonus.isEarned(emptyResults))
        self.assertFalse(bonus.isEarned(noDefeatResults))
        self.assertTrue(bonus.isEarned(mixedResults))
        self.assertTrue(bonus.isEarned(perfectResults))
