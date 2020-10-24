import argparse
import asyncio
import os
from random import randrange
import json
from datetime import datetime, timedelta

import tornado.web
import firebase_admin
from firebase_admin import credentials

from infinitdserver.game import Game
from infinitdserver.game_config import GameConfig
from infinitdserver.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitdserver.logger import Logger

from infinitdserver.handler.user import UserHandler
from infinitdserver.handler.users import UsersHandler
from infinitdserver.handler.this_user import ThisUserHandler
from infinitdserver.handler.register import RegisterHandler
from infinitdserver.handler.game_config import GameConfigHandler
from infinitdserver.handler.battleground_stream import BattlegroundStreamHandler
from infinitdserver.handler.user_stream import UserStreamHandler
from infinitdserver.handler.build import BuildHandler
from infinitdserver.handler.sell import SellHandler
from infinitdserver.handler.wave import WaveHandler
from infinitdserver.handler.control_battle import ControlBattleHandler
from infinitdserver.handler.battle_stream import BattleStreamHandler

async def updateGoldEveryMinute(game: Game):
    oneMinute = timedelta(minutes=1)
    logger: Logger = Logger.getDefault()
    while True:
        startTime = datetime.now()
        await game.accumulateGold()
        endTime = datetime.now()

        # Figure out how long we need to wait
        waitTime = oneMinute - (endTime - startTime)
        if waitTime.seconds > 0:
            await asyncio.sleep(waitTime.seconds)
        else:
            logger.warn("updateGoldEveryMinute", -1, f"updateGoldEveryMinute is running {-waitTime} behind.")

def make_app(game):
    cred = credentials.Certificate("./data/privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(game=game)),
        (r"/user/(.*)", UserHandler, dict(game=game)),
        (r"/userStream/(.*)", UserStreamHandler, dict(game=game)),
        (r"/thisUser", ThisUserHandler, dict(game=game)),
        (r"/register/(.*)", RegisterHandler, dict(game=game)),
        (r"/gameConfig", GameConfigHandler, dict(game=game)),
        (r"/battlegroundStream/(.*)", BattlegroundStreamHandler, dict(game=game)),
        (r"/build/(.*)/([0-9]*)/([0-9]*)", BuildHandler, dict(game=game)),
        (r"/sell/(.*)/([0-9]*)/([0-9]*)", SellHandler, dict(game=game)),
        (r"/wave/(.*)", WaveHandler, dict(game=game)),
        (r"/battle/(.*)", BattleStreamHandler, dict(game=game)),
        (r"/controlBattle/(.*)", ControlBattleHandler, dict(game=game)),
    ], **settings)

async def main():
    parser = argparse.ArgumentParser(description="Backend server for InfiniTD.")
    parser.add_argument('-d', '--debug', action="store_true")
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('-p', '--port', action="store", type=int, default=8794)
    parser.add_argument('--reset-battles', action="store_true")
    args = parser.parse_args()

    with open('game_config.json') as gameConfigFile:
        gameConfig = GameConfig.from_json(gameConfigFile.read())
    Logger.setDefault(Logger("data/logs.db", printVerbosity=args.verbosity, debug=args.debug))
    game = Game(gameConfig, debug=args.debug)
    # Make sure no one is stuck in a battle.
    game.clearInBattle()
    if args.reset_battles:
        game.resetBattles()
    app = make_app(game)
    app.listen(args.port)
    print(f"Listening on port {args.port}.")
    loop = asyncio.get_running_loop()
    gold_task = loop.create_task(updateGoldEveryMinute(game))
    await asyncio.wait([gold_task])

if __name__ == "__main__":
    asyncio.run(main())
