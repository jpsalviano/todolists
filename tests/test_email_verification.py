from falcon import testing
from jinja2 import Environment, FileSystemLoader
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock
from unittest.mock import patch

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
        app.save_token_to_redis("john12@fake.com", "111111")
        with redis_conn.conn as conn:
            self.assertTrue(conn.get("john12@fake.com").decode(), "111111")

    def test_build_sending_code_message_html_body(self):
        body = self.templates_env.get_template("email_message_sending_code.html").render(token="111111")
        result = app.build_email_message_sending_code_html_body("111111")
        self.assertEqual(body, result)

    def test_build_sending_code_message_as_mime_str(self):
        message = app.build_email_message_sending_code("john12@fake.com", "111111")
        result = MIMEMultipart()
        result['Subject'] = "Finish your registration on TodoLists!"
        result['From'] = "TodoLists"
        result['To'] = "john12@fake.com"
        body = app.build_email_message_sending_code_html_body("111111")
        result.attach(MIMEText(body, "html"))
        self.assertTrue("111111" in message)
        self.assertTrue("111111" in result.as_string())
        self.assertEqual(len(result.as_string()), len(message))

    # def test_email_server_connects(self):
    #     self.assertTrue(email_server.connect_server())

    @patch("todolists.app.email_server.connect_server")
    def test_email_server_connects(self, connect_server):
        message = app.build_email_message_sending_code("john12@fake.com", "111111")
        app.send_email_with_code("john12@fake.com", message)
        connect_server.assert_called_once()

    @patch("todolists.app.email_server.send_mail")
    def test_email_server_sends_message_code(self, send_mail):
        message = app.build_email_message_sending_code("john12@fake.com", "111111")
        app.send_email_with_code("john12@fake.com", message)
        send_mail.assert_called_with("john12@fake.com", message)