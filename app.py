import falcon
import json


class UserRegistration:
	def on_get(self, req, resp):
		pass

	def on_post(self, req, resp):
		resp.media = req.params


def create():
	app = api = falcon.API()
	app.add_route("/register", UserRegistration())
	return app

app = create()