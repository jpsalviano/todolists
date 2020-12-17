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
        with app.db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    def test_redirect_to_email_verification_page_after_user_registration_form_submitted(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        template = self.templates_env.get_template("email_verification.html")
        self.assertEqual(result.text, template.render())

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
        self.assertTrue("111111" in result.as_string())
        self.assertEqual(len(result.as_string()), len(message))

    def test_get_credentials(self):
        doc_file = open("todolists/EMAIL_", "r")
        doc = doc_file.read().split("\n")
        result = email_server.get_credentials()
        self.assertEqual(doc, result)

    @patch("todolists.app.email_server.connect_server")
    def test_email_server_connects(self, connect_server):
        message = app.build_email_message_sending_code("john12@fake.com", "111111")
        app.send_email_with_code("john12@fake.com", message)
        connect_server.assert_called_once()

    @patch("todolists.app.email_server.connect_server")
    @patch("todolists.app.email_server.send_mail")
    def test_email_server_sends_message_code(self, send_mail, connect_server):
        message = app.build_email_message_sending_code("john12@fake.com", "111111")
        app.send_email_with_code("john12@fake.com", message)
        app.email_server.send_mail.assert_called_once()

    def test_user_enters_correct_code(self):
        pass
