import asyncio
from typing import Optional, ClassVar, Awaitable, Callable, List, Dict
import json

from dataclasses_json import DataClassJsonMixin
from tornado.websocket import WebSocketHandler
import cattr
from asyncio_multisubscriber_queue import MultisubscriberQueue

from infinitd_server.game import Game
from infinitd_server.logger import Logger
from infinitd_server.handler.base import BaseHandler

class StreamHandler(BaseHandler, WebSocketHandler):
    game: Game
    readTasks: Dict[str, asyncio.Task]

    # Allow cross-origin requests.
    def check_origin(self, origin):
        return True

    def prepare(self):
        super().prepare()
        self.readTasks = {}

    def on_message(self, msg):
        # Parse message to see if it's a request to subscribe/unsubscribe to some data
        if msg[0] == "+":
            return self.subscribe(msg[1:])
        if msg[0] == "-":
            return self.unsubscribe(msg[1:])
        else:
            raise ValueError(f"Got unexpected message: {msg}")

    def on_close(self):
        self.logInfo("Stream connection closed.")
        # Remove self from any queues
        for id in list(self.readTasks.keys()):
            self.unsubscribe(id)
    
    def subscribe(self, id: str):
        if id in self.readTasks:
            self.logWarn(f"Attempted to subscribe to already subscribed queue: {id}")
            return
        
        datatype, dataId = id.split('/', maxsplit=1)
        if dataId is None:
            raise ValueError(f"Could not split subscribe ID: {id}")

        try:
            queueCollection = self.game.queues[datatype]
        except KeyError:
            self.logWarn(f"Attempting to subscribe to unknown datatype: {datatype}")
            return

        # Get the initial state for this new subscription.
        initialData = self.getInitialState(datatype, dataId)
        if initialData is not None:
            self.sendData(id, initialData)

        # Start a queue and a task to ready from that queue.
        qContext = queueCollection.queue_context(dataId)
        async def readFromQ():
            with qContext as q:
                while True:
                    newData = await q.get()
                    self.sendData(id, newData)
        self.readTasks[id] = asyncio.create_task(readFromQ())

    def unsubscribe(self, id: str):
        if id not in self.readTasks:
            self.logWarn(f"Attempted to unsubscribe from not subscribed queue: {id}")
            return
        self.readTasks[id].cancel()
        del self.readTasks[id]

    def open(self):
        pass

    def getInitialState(self, datatype: str, dataId: str):
        if datatype == "user":
            return self.game.getUserSummaryByName(dataId)
        if datatype == "battleground":
            return self.game.getBattleground(dataId)
        if datatype == "battle":
            return self.game.joinBattle(dataId)
        if datatype == "rivals":
            return self.game.getUserRivals(dataId)
        if datatype == "battleGpm":
            defenderName, attackerName = dataId.split('/', maxsplit=1)
            defender = self.game.getUserSummaryByName(defenderName)
            attacker = self.game.getUserSummaryByName(attackerName)
            maybeBattle = self.game.getBattle(attacker = attacker, defender = defender)
            if maybeBattle:
                return maybeBattle.results.goldPerMinute
            return -1.0
        raise ValueError(f"Cannot get initial state for datatype: {datatype}")
    
    def sendData(self, id: str, data):
        if isinstance(data, list):
            for x in data:
                self.sendDataElement(id, x)
        else:
            self.sendDataElement(id, data)

    def sendDataElement(self, id: str, data):
        if isinstance(data, DataClassJsonMixin):
            self.write_message(f"{id}:{data.to_json()}")
        else:
            encoded = json.dumps(cattr.unstructure(data))
            self.write_message(f"{id}:{encoded}")