import asyncio
import unittest.mock
import tempfile
import os

import tornado.testing

from infinitd_server.handler.delete_account import DeleteAccountHandler
from infinitd_server.logger import Logger, MockLogger
from infinitd_server.game import Game
import test_data

class TestResetGameData(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        Logger.setDefault(MockLogger())
        _, tmp_path = tempfile.mkstemp()
        self.dbPath = tmp_path
        self.gameConfig = test_data.gameConfig
        self.game = Game(self.gameConfig, dbPath = self.dbPath)

        self.game.register(uid="test_uid", name="bob")
        self.game.register(uid="test_uid2", name="sam")

        return tornado.web.Application([(r"/deleteAccount/(.*)", DeleteAccountHandler, dict(game=self.game))])
    
    def test_successfulDelete(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify, \
                unittest.mock.patch('firebase_admin.auth.delete_user') as mock_delete:
            mock_verify.return_value = {"uid": "test_uid"}
            mock_delete.return_value = None
            resp = self.fetch("/deleteAccount/bob", method="DELETE")
        user = self.game.getUserSummaryByName("bob")
        users = self.game.getUserSummaries()

        self.assertEqual(resp.code, 204)
        self.assertIsNone(user)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].name, "sam")
        self.assertEqual(users[0].uid, "test_uid2")

    def test_deletedUserCanReregister(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify, \
                unittest.mock.patch('firebase_admin.auth.delete_user') as mock_delete:
            mock_verify.return_value = {"uid": "test_uid"}
            mock_delete.return_value = None
            self.fetch("/deleteAccount/bob", method="DELETE")
        self.game.register(uid="test_uid", name="bob")

        user = self.game.getUserSummaryByName("bob")
        self.assertEqual(user.name, "bob")
        self.assertEqual(user.uid, "test_uid")

    def test_mismatchedName(self):
        with unittest.mock.patch('infinitd_server.handler.base.BaseHandler.verifyAuthentication') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            resp = self.fetch("/deleteAccount/sam", method="DELETE")
        
        self.assertEqual(resp.code, 403)
        # Make sure neither user was deleted.
        bob = self.game.getUserSummaryByName("bob")
        self.assertEqual(bob.name, "bob")
        self.assertEqual(bob.uid, "test_uid")
        sam = self.game.getUserSummaryByName("sam")
        self.assertEqual(sam.name, "sam")
        self.assertEqual(sam.uid, "test_uid2")

    def tearDown(self):
        super().tearDown()
        os.remove(self.dbPath)