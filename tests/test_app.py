import json
from falcon import testing, HTTP_200
from todolists import app


class TestApp(testing.TestCase):
    def setUp(self):
        super(TestApp, self).setUp()

        self.app = app.create()
        self.username = "John123"
        self.email = "john123@fake.com"
        self.password = "abc123-"

    def test_app_status(self):
    	doc = {"message": "ok"}
    	result = self.simulate_get("/status")
    	self.assertEqual(result.json, doc)
    	self.assertEqual(result.status, HTTP_200)

    def test_app_gets_register_page(self):
    	result = self.simulate_get("/register")
    	self.assertEqual(result.status, HTTP_200)

    def test_app_gets_user_info_from_form(self):
    	user_info = {
    		"username": self.username,
    		"email": self.email,
    		"password_1": self.password,
    		"password_2": self.password
    	}
    	result = self.simulate_post("/register", params=user_info)
    	self.assertEqual(result.json, user_info)