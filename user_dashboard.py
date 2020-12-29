import falcon

from todolists import app, db


class UserDashboard:
    def on_get(self, req, resp):
        pass