import tornado.ioloop
import tornado.web
import firebase_admin
import firebase_admin.auth
from firebase_admin import credentials

class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, authorization, content-type")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def options(self, *args):
        print("Got OPTIONS request.")

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

class UidHandler(BaseHandler):
    def get(self, uid):
        print("Got request for UID: %s" % uid)
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                decoded_token = firebase_admin.auth.verify_id_token(token)
                print(decoded_token)
                if uid == decoded_token['uid']:
                    print("Got a matching UID!")
                else:
                    print("GET UID (%s) doesn't match token UID (%s)" % (uid, decoded_token['uid']))
            except Exception as e:
                print(e)
        user = {'displayName': 'Namey McNameName'}
        self.write(user)

def make_app():
    cred = credentials.Certificate("./privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    return tornado.web.Application([
        (r"/users", UsersHandler),
        (r"/user/(.*)", UserHandler),
        (r"/uid/(.*)", UidHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8794)
    tornado.ioloop.IOLoop.current().start()
