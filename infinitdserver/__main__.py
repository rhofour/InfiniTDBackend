import asyncio
import os
from random import randrange
import json

import tornado.web
from tornado.web import Finish
from tornado.iostream import StreamClosedError
import firebase_admin
import firebase_admin.auth
from firebase_admin import credentials
from asyncio_multisubscriber_queue import MultisubscriberQueue

from infinitdserver.db import Db
from infinitdserver.game_config import GameConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState

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
    def get(self):
        print("Got request for /users")
        users = [user.to_dict() for user in self.db.getUsers()]
        data = {'users': users}
        self.write(data)

class UserHandler(BaseDbHandler):
    def get(self, username):
        print("Got request for /user/" + username)
        user = self.db.getUserByName(username)
        if user:
            print("Sending ", str(user.to_dict()))
            self.write(user.to_dict())
        else:
            self.set_status(404)

class ThisUserHandler(BaseDbHandler):
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
    # TODO(rofer): Switch to using response headers to send this.
    # 204 for name found, 404 for not found
    def get(self, name):
        print("Got request for isNameTaken/" + name)
        self.write({"isTaken": self.db.nameTaken(name)})

class RegisterHandler(BaseDbHandler):
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

class BattlegroundStreamer:
    def __init__(self, db):
        self.db = db
        self.queuesByUsername = {}

    def queue_context(self, name: str):
        if name not in self.queuesByUsername:
            self.queuesByUsername[name] = MultisubscriberQueue()
        return self.queuesByUsername[name].queue_context()

    async def sendUpdate(self, name, newBgState):
        if name not in self.queuesByUsername:
            return
        await self.queuesByUsername[name].put(newBgState)

class BattlegroundStateHandler(tornado.web.RequestHandler):
    db: Db
    streamer: BattlegroundStreamer

    def initialize(self, db, streamer):
        self.db = db
        self.streamer = streamer
        self.streamerId = None

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "content-type")
        self.set_header("Access-Control-Allow-Methods", "GET")
        self.set_header("content-type", "text/event-stream")
        self.set_header("cache-control", "no-cache")

    async def publish(self, data):
        self.write(f"data: {data.to_json()}\n\n")
        await self.flush()

    async def get(self, username):
        # Send initial battleground state from database
        with self.streamer.queue_context(username) as q:
            try:
                initial_state = random_state()
                await self.publish(initial_state)
                while True:
                    newBgState = await q.get()
                    await self.publish(newBgState)
            except StreamClosedError:
                print("Stream closed.");

async def sendRandomStates(streamer, user):
    while True:
        print("Sending a random update")
        await streamer.sendUpdate(user, random_state())
        await asyncio.sleep(10)

def random_state():
    towers = [[None for c in range(10)] for r in range(14)]
    towers[randrange(14)][randrange(10)] = BgTowerState(id=1)
    towers[randrange(14)][randrange(10)] = BgTowerState(id=0)
    return BattlegroundState(towers=BgTowersState(towers))

def make_app(db, bgStreamer, gameConfig):
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
        (r"/battleground/(.*)", BattlegroundStateHandler, dict(db=db, streamer=bgStreamer)),
    ], **settings)

async def main():
    db = Db(debug=True)
    bgStreamer = BattlegroundStreamer(db)
    with open('game_config.json') as gameConfigFile:
        game_config = GameConfig.from_json(gameConfigFile.read())
    app = make_app(db, bgStreamer, game_config)
    app.listen(8794)
    print("Listening on port 8794.")
    loop = asyncio.get_running_loop()
    task = loop.create_task(sendRandomStates(bgStreamer, "rofer"))
    await asyncio.wait([task])

if __name__ == "__main__":
    asyncio.run(main())
