import argparse
import asyncio
import os
from random import randrange
import json
from datetime import datetime, timedelta

import cattr
import tornado.web
import firebase_admin
from firebase_admin import credentials

from infinitd_server.game import Game
from infinitd_server.game_config import GameConfig, GameConfigData
from infinitd_server.battleground_state import BattlegroundState, BgTowersState, BgTowerState
from infinitd_server.logger import Logger

from infinitd_server.handler.user import UserHandler
from infinitd_server.handler.users import UsersHandler
from infinitd_server.handler.this_user import ThisUserHandler
from infinitd_server.handler.register import RegisterHandler
from infinitd_server.handler.game_config import GameConfigHandler
from infinitd_server.handler.battleground_stream import BattlegroundStreamHandler
from infinitd_server.handler.user_stream import UserStreamHandler
from infinitd_server.handler.build import BuildHandler
from infinitd_server.handler.sell import SellHandler
from infinitd_server.handler.wave import WaveHandler
from infinitd_server.handler.control_battle import ControlBattleHandler
from infinitd_server.handler.battle_stream import BattleStreamHandler
from infinitd_server.handler.recorded_battle import RecordedBattleHandler
from infinitd_server.handler.debug_logs import DebugLogsHandler

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

def make_app(game, debug):
    cred = credentials.Certificate("./data/privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    prod_handlers = [
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
        (r"/battleStream/(.*)", BattleStreamHandler, dict(game=game)),
        (r"/controlBattle/(.*)", ControlBattleHandler, dict(game=game)),
        (r"/battle/(.*)/(.*)", RecordedBattleHandler, dict(game=game)),
    ]
    debug_handlers = [
        (r"/debug/logs", DebugLogsHandler, dict(game=game)),
    ]
    return tornado.web.Application(prod_handlers + debug_handlers, **settings)

async def main():
    parser = argparse.ArgumentParser(description="Backend server for InfiniTD.")
    parser.add_argument('-d', '--debug', action="store_true")
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('-p', '--port', action="store", type=int, default=8794)
    parser.add_argument('--reset-battles', action="store_true")
    args = parser.parse_args()

    with open('game_config.json') as gameConfigFile:
        gameConfigData = cattr.structure(json.loads(gameConfigFile.read()), GameConfigData)
        gameConfig = GameConfig.fromGameConfigData(gameConfigData)
    logger = Logger("data/logs.db", printVerbosity=args.verbosity, debug=args.debug)
    Logger.setDefault(logger)
    logger.info("startup", -1, f"Starting with options {args}.")
    game = Game(gameConfig, debug=args.debug)
    # Make sure no one is stuck in a battle.
    game.clearInBattle()
    if args.reset_battles:
        game.resetBattles()
    app = make_app(game, args.debug)
    app.listen(args.port)
    logger.info("startup", -1, f"Listening on port {args.port}.")
    await updateGoldEveryMinute(game)

if __name__ == "__main__":
    asyncio.run(main())
