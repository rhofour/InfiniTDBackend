import argparse
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
from infinitdserver.battle_coordinator import BattleCoordinator
from infinitdserver.sse import SseQueues
from infinitdserver.logger import Logger

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
from infinitdserver.handler.sell import SellHandler
from infinitdserver.handler.wave import WaveHandler
from infinitdserver.handler.battle import BattleHandler
from infinitdserver.handler.battle_stream import BattleStreamHandler

async def updateGoldEveryMinute(db):
    oneMinute = timedelta(minutes=1)
    logger: Logger = Logger.getDefault()
    while True:
        startTime = datetime.now()
        await db.accumulateGold()
        endTime = datetime.now()

        # Figure out how long we need to wait
        waitTime = oneMinute - (endTime - startTime)
        if waitTime.seconds > 0:
            await asyncio.sleep(waitTime.seconds)
        else:
            logger.warn("updateGoldEveryMinute", -1, f"updateGoldEveryMinute is running {-waitTime} behind.")

def make_app(db, queues, gameConfig, battleCoordinator):
    cred = credentials.Certificate("./data/privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(db=db)),
        (r"/user/(.*)", UserHandler, dict(db=db)),
        (r"/userStream/(.*)", UserStreamHandler, dict(db=db, queues=queues['user'])),
        (r"/isNameTaken/(.*)", NameTakenHandler, dict(db=db)),
        (r"/thisUser", ThisUserHandler, dict(db=db)),
        (r"/register/(.*)", RegisterHandler, dict(db=db)),
        (r"/gameConfig", GameConfigHandler, dict(gameConfig=gameConfig)),
        (r"/battlegroundStream/(.*)", BattlegroundStateHandler, dict(db=db, queues=queues['battleground'])),
        (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler, dict(db=db, gameConfig=gameConfig)),
        (r"/sell/(.*)/([0-9]*)/([0-9]*)", SellHandler, dict(db=db, gameConfig=gameConfig)),
        (r"/wave/(.*)", WaveHandler, dict(db=db, gameConfig=gameConfig)),
        (r"/battle/(.*)", BattleStreamHandler, dict(db=db, queues=queues['battle'],
            battleCoordinator=battleCoordinator)),
        (r"/controlBattle/(.*)", BattleHandler, dict(db=db, battleCoordinator=battleCoordinator)),
    ], **settings)

async def main():
    parser = argparse.ArgumentParser(description="Backend for InfiniTD.")
    parser.add_argument('-d', '--debug', action="store_true")
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('-p', '--port', action="store", type=int, default=8794)
    args = parser.parse_args()

    with open('game_config.json') as gameConfigFile:
        gameConfig = GameConfig.from_json(gameConfigFile.read())
    queues = {}
    for queueName in ['battle', 'battleground', 'user']:
        queues[queueName] = SseQueues()
    battleCoordinator = BattleCoordinator(queues['battle'])
    Logger.setDefault(Logger("data/logs.db", printVerbosity=args.verbosity, debug=args.debug))
    db = Db(gameConfig = gameConfig, userQueues = queues['user'], bgQueues = queues['battleground'],
            battleCoordinator = battleCoordinator, debug=args.debug)
    # Make sure no one is stuck in a battle.
    db.clearInBattle()
    app = make_app(db, queues, gameConfig, battleCoordinator)
    app.listen(args.port)
    print(f"Listening on port {args.port}.")
    loop = asyncio.get_running_loop()
    gold_task = loop.create_task(updateGoldEveryMinute(db))
    await asyncio.wait([gold_task])

if __name__ == "__main__":
    asyncio.run(main())
