from falcon import testing
from jinja2 import Environment, FileSystemLoader
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from todolists import redis_conn, app, email_server


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
        self.assertTrue(token.isdecimal())

    def test_save_token_to_redis(self):
        token = app.create_token()
        app.save_token_to_redis("john12@fake.com", token)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get("john12@fake.com").decode(), token)

    def test_email_verification_builds_sending_code_message_body(self):
        token = app.create_token()
        app.save_token_to_redis("john12@fake.com", token)
        body = self.templates_env.get_template("email_message_sending_code.html").render(token=token)
        result = app.build_body(token)
        self.assertEqual(body, result)

    def test_email_verification_builds_mime_str_message(self):
        token = app.create_token()
        app.save_token_to_redis("john12@fake.com", token)
        message = app.build_email_message_sending_code("john12@fake.com", token)
        result = MIMEMultipart()
        result['Subject'] = "Finish your registration on TodoLists!"
        result['From'] = "TodoLists"
        result['To'] = "john12@fake.com"
        result.attach(MIMEText(app.build_body(token), "html"))
        self.assertTrue(token in message)
        self.assertTrue(token in result.as_string())
        self.assertEqual(len(result.as_string()), len(message))

    # def test_email_server_connects(self):
    #     self.assertTrue(email_server.connect_server())