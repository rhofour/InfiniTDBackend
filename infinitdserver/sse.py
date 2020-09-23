import abc
import json
from typing import Dict

import tornado.web
from tornado.iostream import StreamClosedError
from asyncio_multisubscriber_queue import MultisubscriberQueue
from dataclasses_json import DataClassJsonMixin
import cattr

class SseQueues:
    queuesByParam: Dict[str, MultisubscriberQueue]

    def __init__(self):
        self.queuesByParam = {}

    def queue_context(self, param: str):
        if param not in self.queuesByParam:
            self.queuesByParam[param] = MultisubscriberQueue()
        return self.queuesByParam[param].queue_context()

    async def sendUpdate(self, param: str, newState):
        if param not in self.queuesByParam:
            return
        await self.queuesByParam[param].put(newState)

    def __contains__(self, item):
        return item in self.queuesByParam

class SseStreamHandler(tornado.web.RequestHandler, metaclass=abc.ABCMeta):
    queues: SseQueues

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "content-type")
        self.set_header("Access-Control-Allow-Methods", "GET")
        self.set_header("content-type", "text/event-stream")
        self.set_header("cache-control", "no-cache")

    async def publish(self, data):
        if isinstance(data, list):
            for x in data:
                self.publishElement(x)
        else:
            self.publishElement(data)
        await self.flush()

    def publishElement(self, element):
        if isinstance(element, DataClassJsonMixin):
            self.write(f"data: {element.to_json()}\n\n")
        else:
            encoded = json.dumps(cattr.unstructure(element))
            self.write(f"data: {encoded}\n\n")

    async def get(self, param):
        with self.queues.queue_context(param) as q:
            try:
                initialState = await self.initialState(param)
                if initialState is None:
                    self.set_status(404)
                    return
                await self.publish(initialState)
                while True:
                    newState = await q.get()
                    await self.publish(newState)
            except StreamClosedError:
                pass

    @abc.abstractmethod
    async def initialState(self, param):
        pass
