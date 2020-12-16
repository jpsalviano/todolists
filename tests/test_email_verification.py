from falcon import testing
from jinja2 import Environment, FileSystemLoader

from todolists import redis_conn
from todolists import app


class TestEmailVerification(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()
        self.templates_env = Environment(
                             loader=FileSystemLoader('todolists/templates'),
                             autoescape=True,
                             trim_blocks=True,
                             lstrip_blocks=True)

    def tearDown(self):
        with redis_conn.conn as conn:
            conn.flushall()

    def test_create_token_for_email_verification(self):
        token = app.create_token()
        self.assertTrue(len(token), 6)
        self.assertTrue((int))

    def test_save_token_to_redis(self):
        email = "john12@fake.com"
        token = app.create_token()
        app.save_token_to_redis(email, token)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get(email).decode(), token)

    def test_send_token_to_email(self):
        email = "john12@fake.com"
        