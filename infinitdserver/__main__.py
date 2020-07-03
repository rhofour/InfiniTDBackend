import tornado.ioloop
import tornado.web

class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "GET")

class UsersHandler(BaseHandler):
    def get(self):
        print("Got request for /users")
        users = [ {'name': 'rofer', 'accumulatedGold': 3.0, 'goldPerMinute': 0.0} ]
        data = {'users': users}
        self.write(data)

class UserHandler(BaseHandler):
    def get(self, username):
        print("Got request for /user/" + username)
        user = {'name': username, 'accumulatedGold': 42.0, 'goldPerMinute': 0.0}
        self.write(user)

def make_app():
    return tornado.web.Application([
        (r"/users", UsersHandler),
        (r"/user/(.*)", UserHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8794)
    tornado.ioloop.IOLoop.current().start()
