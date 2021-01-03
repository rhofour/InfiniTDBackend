import abc
from typing import Dict

from asyncio_multisubscriber_queue import MultisubscriberQueue

class SseQueues:
    "A queue for implementing Server-Sent Events."
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
    
    def keys(self):
        return self.queuesByParam.keys()