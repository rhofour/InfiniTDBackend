import tornado.ioloop
import tornado.web
import firebase_admin
import firebase_admin.auth
from firebase_admin import credentials

from db import Db

class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, db):
        self.db = db

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, authorization, content-type")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def options(self, *args):
        print("Got OPTIONS request.")

    def verifyAuthentication(self):
        if self.request.headers['authorization'][:7] == "Bearer ":
            token = self.request.headers['authorization'][7:]
            try:
                return firebase_admin.auth.verify_id_token(token)
            except Exception as e:
                print(e)
        self.reply401()


    def reply401(self):
        self.set_status(401)
        self.set_header("WWW-Authenticate", 'Bearer')
        raise Finish()

class UsersHandler(BaseHandler):
    def get(self):
        print("Got request for /users")
        users = self.db.getUsers()
        data = {'users': users}
        self.write(data)

class UserHandler(BaseHandler):
    def get(self, username):
        print("Got request for /user/" + username)
        userData = self.db.getUserByName(username)
        user = {"name": username, "accumulatedGold": 42.0, "goldPerMinute": 0.0}
        if userData:
            print("Sending ", str(userData))
            self.write(userData)
        else:
            self.write({})

class ThisUserHandler(BaseHandler):
    def get(self):
        print("Got request for thisUser")
        decoded_token = self.verifyAuthentication()
        userData = self.db.getUserByUid(decoded_token["uid"])
        if userData:
            print("Sending ", str(userData))
            self.write(userData)
        else:
            self.write({})

def make_app():
    cred = credentials.Certificate("./privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    db = Db(debug=True)
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(db=db)),
        (r"/user/(.*)", UserHandler, dict(db=db)),
        (r"/thisUser", ThisUserHandler, dict(db=db)),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8794)
    tornado.ioloop.IOLoop.current().start()
