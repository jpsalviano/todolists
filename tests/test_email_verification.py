from falcon import testing
from jinja2 import Environment, FileSystemLoader
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from unittest.mock import patch

from todolists import redis_conn, app, email_server


class TestEmailVerification(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()

    def tearDown(self):
        with redis_conn.conn as conn:
            conn.flushall()
        with app.db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    @patch("todolists.app.email_server.connect_server")
    @patch("todolists.app.email_server.send_mail")
    def test_get_email_verification_html_after_registration_form_submitted(self, connect_server,\
                                                                                   send_mail):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        template = app.templates_env.get_template("email_verification.html")
        self.assertEqual(result.text, template.render())

    def test_create_token_for_email_verification(self):
        token = app.create_token()
        self.assertTrue(len(token), 6)
        self.assertTrue(token.isdecimal())

    def test_save_token_to_redis(self):
        app.save_token_to_redis("111111", "john12@fake.com")
        with redis_conn.conn as conn:
            self.assertTrue(conn.get("111111").decode(), "john12@fake.com")

    def test_build_sending_token_message_html_body(self):
        body = app.templates_env.get_template("email_message_sending_code.html").render(token="111111")
        result = app.build_email_message_sending_token_html_body("111111")
        self.assertEqual(body, result)

    def test_build_sending_token_message_as_mime_str(self):
        message = app.build_email_message_sending_token("john12@fake.com", "111111")
        doc = MIMEMultipart()
        doc['Subject'] = "Finish your registration on TodoLists!"
        doc['From'] = "TodoLists"
        doc['To'] = "john12@fake.com"
        body = app.build_email_message_sending_token_html_body("111111")
        doc.attach(MIMEText(body, "html"))
        self.assertTrue("111111" in doc.as_string())
        self.assertEqual(len(doc.as_string()), len(message))

    def test_get_credentials(self):
        with open("todolists/EMAIL_", "r") as doc_file:
            doc = doc_file.read().split("\n")
        result = email_server.get_credentials()
        self.assertEqual(doc, result)

    @patch("todolists.app.email_server.connect_server")
    def test_email_server_connects(self, connect_server):
        app.send_email_with_token("john12@fake.com")
        connect_server.assert_called_once()

    @patch("todolists.app.email_server.connect_server")
    @patch("todolists.app.email_server.send_mail")
    def test_email_server_sends_message_token(self, send_mail, connect_server):
        app.send_email_with_token("john12@fake.com")
        app.email_server.send_mail.assert_called_once()

    def test_email_verification_gets_correct_email_from_redis(self):
        app.save_token_to_redis("111111", "john12@fake.com")
        self.assertEqual(app.get_email("111111"), "john12@fake.com")

    def test_update_user_verified_in_db(self):
        app.save_user_to_db("john12", "john12@fake.com",
                            "$2b$12$SarrTn1SWbB2/k.JugfBSOgpLIumfkzuSKXlCImDsKghyRHttUxxm")
        app.update_user_verified_in_db("john12@fake.com")
        with app.db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT verified FROM users WHERE email='john12@fake.com'")
                self.assertTrue(curs.fetchone().verified)

    def test_successful_registration_page_when_correct_token_is_entered(self):
        app.save_token_to_redis("111111", "john12@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111111"})
        template = app.templates_env.get_template("successful_registration.html")
        self.assertEqual(result.text, template.render())

    def test_get_error_page_if_token_entered_is_wrong(self):
        app.save_token_to_redis("111111", "john12@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111112"})
        template = app.templates_env.get_template("error.html")
        self.assertEqual(result.text, template.render(error="The code entered is either wrong or expired."))