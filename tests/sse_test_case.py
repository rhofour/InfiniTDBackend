import asyncio

import tornado.testing

class SseTestCase(tornado.testing.AsyncHTTPTestCase):
    def fetchSse(self, url, expectations):
        callback_calls = 0
        def callback(x):
            nonlocal callback_calls
            self.assertEqual(x[:6], b"data: ")
            expectations[callback_calls](x[6:])
            callback_calls += 1
            if len(expectations) == callback_calls:
                self.stop()

        self.http_client.fetch(
            self.get_url(url),
            streaming_callback=callback)