import asyncio
import os
from random import randrange
import json
from datetime import datetime, timedelta

import tornado.web
from tornado.web import Finish
import firebase_admin
import firebase_admin.auth
from firebase_admin import credentials

from infinitdserver.db import Db
from infinitdserver.game_config import GameConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.sse import SseStreamHandler, SseQueues

class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, authorization, content-type")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")

    def options(self, *args):
        print("Got OPTIONS request.")

    def reply401(self):
        self.set_status(401)
        self.set_header("WWW-Authenticate", 'Bearer')
        raise Finish()

class BaseDbHandler(BaseHandler):
    db: Db

    def initialize(self, db):
        self.db = db

    def verifyAuthentication(self):
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                return firebase_admin.auth.verify_id_token(token)
            except Exception as e:
                print(e)
        self.reply401()

class UsersHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self):
        print("Got request for /users")
        users = [user.to_dict() for user in self.db.getUsers()]
        data = {'users': users}
        self.write(data)

class UserHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self, username):
        print("Got request for /user/" + username)
        user = self.db.getUserByName(username)
        if user:
            print("Sending ", str(user.to_dict()))
            self.write(user.to_dict())
        else:
            self.set_status(404)

class ThisUserHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def get(self):
        print("Got request for thisUser")
        decoded_token = self.verifyAuthentication()
        user = self.db.getUserByUid(decoded_token["uid"])
        if user:
            print("Sending back ", str(user.to_dict()))
            self.write(user.to_dict())
        else:
            print("No user data found.")
            self.write({})

class NameTakenHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    # TODO(rofer): Switch to using response headers to send this.
    # 204 for name found, 404 for not found
    def get(self, name):
        print("Got request for isNameTaken/" + name)
        self.write({"isTaken": self.db.nameTaken(name)})

class RegisterHandler(BaseDbHandler):
    db: Db # See https://github.com/google/pytype/issues/652

    def post(self, name):
        print("Got request for register/" + name)
        decoded_token = self.verifyAuthentication()
        if (self.db.register(uid=decoded_token["uid"], name=name)):
            self.set_status(201); # CREATED
        else:
            self.set_status(412); # Precondition Failed (assume name is already used)

class GameConfigHandler(BaseHandler):
    gameConfig: GameConfig

    def initialize(self, gameConfig):
        self.gameConfig = gameConfig

    def get(self):
        self.write(self.gameConfig.to_dict())

class BattlegroundStateHandler(SseStreamHandler):
    db: Db
    queues: SseQueues

    def initialize(self, db, queues):
        self.db = db
        self.queues = queues

    async def initialState(self, name):
        return self.db.getBattleground(name)

def random_state():
    towers = [[None for c in range(10)] for r in range(14)]
    towers[randrange(14)][randrange(10)] = BgTowerState(id=1)
    towers[randrange(14)][randrange(10)] = BgTowerState(id=0)
    return BattlegroundState(towers=BgTowersState(towers))

async def updateGoldEveryMinute(db):
    oneMinute = timedelta(minutes=1)
    while True:
        print("Accumulating gold.")
        startTime = datetime.now()
        db.accumulateGold()
        endTime = datetime.now()

        # Figure out how long we need to wait
        waitTime = oneMinute - (endTime - startTime)
        if waitTime.seconds > 0:
            await asyncio.sleep(waitTime.seconds)
        else:
            print("updateGoldEveryMinute is running {-waitTime} behind.")

def make_app(db, bgQueues, gameConfig):
    cred = credentials.Certificate("./privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(db=db)),
        (r"/user/(.*)", UserHandler, dict(db=db)),
        (r"/isNameTaken/(.*)", NameTakenHandler, dict(db=db)),
        (r"/thisUser", ThisUserHandler, dict(db=db)),
        (r"/register/(.*)", RegisterHandler, dict(db=db)),
        (r"/gameConfig", GameConfigHandler, dict(gameConfig=gameConfig)),
        (r"/battleground/(.*)", BattlegroundStateHandler, dict(db=db, queues=bgQueues)),
    ], **settings)

async def main():
    with open('game_config.json') as gameConfigFile:
        gameConfig = GameConfig.from_json(gameConfigFile.read())
    db = Db(gameConfig = gameConfig, debug=True)
    bgQueues = SseQueues()
    app = make_app(db, bgQueues, gameConfig)
    app.listen(8794)
    print("Listening on port 8794.")
    loop = asyncio.get_running_loop()
    gold_task = loop.create_task(updateGoldEveryMinute(db))
    await asyncio.wait([gold_task])

if __name__ == "__main__":
    asyncio.run(main())
