import asyncio
import os
from random import randrange
import json
from datetime import datetime, timedelta

import tornado.web
import firebase_admin
from firebase_admin import credentials

from infinitdserver.db import Db
from infinitdserver.game_config import GameConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.sse import SseQueues
from infinitdserver.handler.base import BaseHandler, BaseDbHandler
from infinitdserver.handler.user import UserHandler
from infinitdserver.handler.users import UsersHandler
from infinitdserver.handler.this_user import ThisUserHandler
from infinitdserver.handler.name_taken import NameTakenHandler
from infinitdserver.handler.register import RegisterHandler
from infinitdserver.handler.game_config import GameConfigHandler
from infinitdserver.handler.battleground_state import BattlegroundStateHandler
from infinitdserver.handler.user_stream import UserStreamHandler
from infinitdserver.handler.build import BuildHandler

async def updateGoldEveryMinute(db):
    oneMinute = timedelta(minutes=1)
    while True:
        startTime = datetime.now()
        await db.accumulateGold()
        endTime = datetime.now()

        # Figure out how long we need to wait
        waitTime = oneMinute - (endTime - startTime)
        if waitTime.seconds > 0:
            await asyncio.sleep(waitTime.seconds)
        else:
            print("updateGoldEveryMinute is running {-waitTime} behind.")

def make_app(db, userQueues, bgQueues, gameConfig):
    cred = credentials.Certificate("./privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(db=db)),
        (r"/user/(.*)", UserHandler, dict(db=db)),
        (r"/userStream/(.*)", UserStreamHandler, dict(db=db, queues=userQueues)),
        (r"/isNameTaken/(.*)", NameTakenHandler, dict(db=db)),
        (r"/thisUser", ThisUserHandler, dict(db=db)),
        (r"/register/(.*)", RegisterHandler, dict(db=db)),
        (r"/gameConfig", GameConfigHandler, dict(gameConfig=gameConfig)),
        (r"/battlegroundStream/(.*)", BattlegroundStateHandler, dict(db=db, queues=bgQueues)),
        (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler, dict(db=db, gameConfig=gameConfig)),
    ], **settings)

async def main():
    with open('game_config.json') as gameConfigFile:
        gameConfig = GameConfig.from_json(gameConfigFile.read())
    userQueues = SseQueues()
    db = Db(gameConfig = gameConfig, userQueues = userQueues, debug=True)
    bgQueues = SseQueues()
    app = make_app(db, userQueues, bgQueues, gameConfig)
    app.listen(8794)
    print("Listening on port 8794.")
    loop = asyncio.get_running_loop()
    gold_task = loop.create_task(updateGoldEveryMinute(db))
    await asyncio.wait([gold_task])

if __name__ == "__main__":
    asyncio.run(main())
