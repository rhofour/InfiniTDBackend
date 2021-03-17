import argparse
import asyncio
import os
from random import randrange
import json
from datetime import datetime, timedelta
import ssl
import signal

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
from infinitd_server.handler.delete_account import DeleteAccountHandler
from infinitd_server.handler.debug_logs import DebugLogsHandler
from infinitd_server.handler.debug_battle_input import DebugBattleInputHandler
from infinitd_server.handler.admin.reset_game import ResetGameHandler
from infinitd_server.handler.rivals_stream import RivalsStreamHandler
from infinitd_server.handler.stream import StreamHandler

def make_app(game, debug):
    cred = credentials.Certificate("./data/privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
        "debug": debug,
        "autoreload": False,
    }
    prod_handlers = [
        (r"/users", UsersHandler, dict(game=game)),
        (r"/user/(.*)", UserHandler, dict(game=game)),
        (r"/userStream/(.*)", UserStreamHandler, dict(game=game)),
        (r"/thisUser", ThisUserHandler, dict(game=game)),
        (r"/register/(.*)", RegisterHandler, dict(game=game)),
        (r"/gameConfig", GameConfigHandler, dict(game=game)),
        (r"/battlegroundStream/(.*)", BattlegroundStreamHandler, dict(game=game)),
        (r"/build/(.*)", BuildHandler, dict(game=game)),
        (r"/sell/(.*)", SellHandler, dict(game=game)),
        (r"/wave/(.*)", WaveHandler, dict(game=game)),
        (r"/battleStream/(.*)", BattleStreamHandler, dict(game=game)),
        (r"/controlBattle/(.*)", ControlBattleHandler, dict(game=game)),
        (r"/battle/(.*)/(.*)", RecordedBattleHandler, dict(game=game)),
        (r"/deleteAccount/(.*)", DeleteAccountHandler, dict(game=game)),
        (r"/rivalsStream/(.*)", RivalsStreamHandler, dict(game=game)),
        (r"/stream", StreamHandler, dict(game=game)),
        # Admin actions
        (r"/admin/resetGame", ResetGameHandler, dict(game=game)),
    ]
    debug_handlers = [
        (r"/debug/logs", DebugLogsHandler, dict(game=game)),
        (r"/debug/battleInput/(.*)/(.*)", DebugBattleInputHandler, dict(game=game)),
    ]
    return tornado.web.Application(prod_handlers + debug_handlers, **settings)

def sig_exit(signum, frame):
    tornado.ioloop.IOLoop.instance().add_callback_from_signal(shutdown)

def shutdown():
    Logger.getDefault().info("shutdown", -1, "Shutting down.")
    tornado.ioloop.IOLoop.instance().stop()

def main():
    parser = argparse.ArgumentParser(description="Backend server for InfiniTD.")
    parser.add_argument('-d', '--debug', action="store_true")
    parser.add_argument('-v', '--verbosity', action="store", type=int, default=0)
    parser.add_argument('-p', '--port', action="store", type=int, default=8794)
    parser.add_argument('--reset-battles', action="store_true")
    parser.add_argument('--ssl_cert', action="store", type=str, default="localhost.crt")
    parser.add_argument('--ssl_key', action="store", type=str, default="localhost.key")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, sig_exit)

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
    useSsl = True
    if args.ssl_cert == "":
        logger.info("startup", -1, "No SSL certificate found. Running HTTP only.")
        useSsl = False
    if args.ssl_key == "":
        logger.info("startup", -1, "No SSL key found. Running HTTP only.")
        useSsl = False
    if useSsl:
        sslContext = {
            "certfile": args.ssl_cert,
            "keyfile": args.ssl_key,
        }
        app.listen(args.port, ssl_options=sslContext)
        logger.info("startup", -1, f"Listening on port {args.port} (with SSL enabled) as PID {os.getpid()}.")
    else:
        app.listen(args.port)
        logger.info("startup", -1, f"Listening on port {args.port} (without SSL enabled) as PID {os.getpid()}.")
    async def accumulateGold():
        await game.accumulateGold()
    tornado.ioloop.PeriodicCallback(accumulateGold, 60_000).start()
    async def schedulePeriodicCallbackIn(seconds: float, callback, period: float):
        await asyncio.sleep(seconds)
        tornado.ioloop.PeriodicCallback(callback, period).start()
    async def calculateMissingBattles():
        await game.calculateMissingBattles()
    loop = asyncio.get_event_loop()
    # Schedule this out-of-phase with accumulateGold
    scheduleCallbackTask = loop.create_task(
        schedulePeriodicCallbackIn(30, calculateMissingBattles, 60_000))
    logger.info("startup", -1, "Startup finished.")
    loop.run_until_complete(scheduleCallbackTask)
    loop.run_forever()

if __name__ == "__main__":
    main()