import unittest
import tempfile
import os

from infinitdserver.db import Db
from infinitdserver.battleground_state import BattlegroundState

class TestDb(unittest.TestCase):
    def setUp(self):
        tmp_file, tmp_path = tempfile.mkstemp()
        self.db_path = tmp_path
        self.db = Db(db_path=self.db_path)

    def test_registerNewUser(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

    def test_registerSameUserFails(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))
        # Test identical user
        self.assertFalse(self.db.register(uid="foo", name="bob"))
        # Test identical name
        self.assertFalse(self.db.register(uid="bar", name="bob"))
        # Test identical uid
        self.assertFalse(self.db.register(uid="foo", name="joe"))

    def test_getUserByName(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        user = self.db.getUserByName("bob")

        self.assertEqual(user["name"], "bob")

    def test_getBattleground(self):
        self.assertTrue(self.db.register(uid="foo", name="bob"))

        bg = self.db.getBattleground("bob")
        self.assertIsNone(self.db.getBattleground("unknown_username"))

        print(bg)
        print(type(bg))
        self.assertIs(type(bg), BattlegroundState)

    def tearDown(self):
        os.remove(self.db_path)

if __name__ == "__main__":
    unittest.main()
