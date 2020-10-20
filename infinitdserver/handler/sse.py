import abc
import json

from dataclasses_json import DataClassJsonMixin
from tornado.iostream import StreamClosedError
import cattr

from infinitdserver.sse import SseQueues
from infinitdserver.game import Game
from infinitdserver.handler.base import BaseHandler

class SseStreamHandler(BaseHandler, metaclass=abc.ABCMeta):
    "A base handler for implementing Server-Sent Events."
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
