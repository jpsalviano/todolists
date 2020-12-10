import falcon
import json


class Status:
	def on_get(self, req, resp):
		resp.media = {"message": "ok"}
		resp.status = falcon.HTTP_200


class Register:
	def on_get(self, req, resp):
		resp.status = falcon.HTTP_200

	def on_post(self, req, resp):
		resp.body = json.dumps(req.params)


def create():
	app = api = falcon.API()
	app.add_route("/status", Status())
	app.add_route("/register", Register())
	return app

app = create()