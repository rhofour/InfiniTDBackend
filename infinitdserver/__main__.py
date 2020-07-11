import os
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
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")

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
            self.set_status(404)

class ThisUserHandler(BaseHandler):
    def get(self):
        print("Got request for thisUser")
        decoded_token = self.verifyAuthentication()
        userData = self.db.getUserByUid(decoded_token["uid"])
        if userData:
            print("Sending back ", str(userData))
            self.write(userData)
        else:
            print("No user data found.")
            self.write({})

class NameTakenHandler(BaseHandler):
    # TODO(rofer): Switch to using response headers to send this.
    # 204 for name found, 404 for not found
    def get(self, name):
        print("Got request for isNameTaken/" + name)
        self.write({"isTaken": self.db.nameTaken(name)})

class RegisterHandler(BaseHandler):
    def post(self, name):
        print("Got request for register/" + name)
        decoded_token = self.verifyAuthentication()
        if (self.db.register(uid=decoded_token["uid"], name=name)):
            self.set_status(201); # CREATED
        else:
            self.set_status(412); # Precondition Failed (assume name is already used)

def make_app():
    cred = credentials.Certificate("./privateFirebaseKey.json")
    firebase_admin.initialize_app(cred)
    db = Db(debug=True)
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    }
    return tornado.web.Application([
        (r"/users", UsersHandler, dict(db=db)),
        (r"/user/(.*)", UserHandler, dict(db=db)),
        (r"/isNameTaken/(.*)", NameTakenHandler, dict(db=db)),
        (r"/thisUser", ThisUserHandler, dict(db=db)),
        (r"/register/(.*)", RegisterHandler, dict(db=db)),
    ], **settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8794)
    print("Listening on port 8794.")
    tornado.ioloop.IOLoop.current().start()
