from falcon import testing
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from unittest.mock import patch

from todolists import email_verification, db, redis_conn, app, email_server
from todolists.user_registration import save_user_to_db



class TestEmailVerification(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()

    def tearDown(self):
        with redis_conn.conn as conn:
            conn.flushall()
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    @patch("todolists.email_server.connect_server")
    @patch("todolists.email_server.send_mail")
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
        token = email_verification.create_token()
        self.assertTrue(len(token), 6)
        self.assertTrue(token.isdecimal())

    def test_save_token_to_redis(self):
        email_verification.save_token_to_redis("111111", "john12@fake.com")
        with redis_conn.conn as conn:
            self.assertTrue(conn.get("111111").decode(), "john12@fake.com")

    def test_build_sending_token_message_html_body(self):
        body = app.templates_env.get_template("email_message_sending_code.html").render(token="111111")
        result = email_verification.build_email_message_sending_token_html_body("111111")
        self.assertEqual(body, result)

    def test_build_sending_token_message_as_mime_str(self):
        message = email_verification.build_email_message_sending_token("john12@fake.com", "111111")
        doc = MIMEMultipart()
        doc['Subject'] = "Finish your registration on TodoLists!"
        doc['From'] = "TodoLists"
        doc['To'] = "john12@fake.com"
        body = email_verification.build_email_message_sending_token_html_body("111111")
        doc.attach(MIMEText(body, "html"))
        self.assertTrue("111111" in doc.as_string())
        self.assertEqual(len(doc.as_string()), len(message))

    def test_get_credentials(self):
        with open("todolists/EMAIL_", "r") as doc_file:
            doc = doc_file.read().split("\n")
        result = email_server.get_credentials()
        self.assertEqual(doc, result)

    @patch("todolists.email_server.connect_server")
    def test_email_server_is_called_with_user_email(self, connect_server):
        email_verification.send_email_with_token("john12@fake.com")
        connect_server.assert_called_once()

    @patch("todolists.email_server.connect_server")
    @patch("todolists.email_server.send_mail")
    def test_email_server_sends_message_token(self, send_mail, connect_server):
        email_verification.send_email_with_token("john12@fake.com")
        email_server.send_mail.assert_called_once()

    def test_email_verification_gets_correct_email_value_from_redis(self):
        email_verification.save_token_to_redis("111111", "john12@fake.com")
        self.assertEqual(email_verification.get_email_by_token("111111"), "john12@fake.com")

    def test_update_user_verified_in_db(self):
        save_user_to_db("John", "john12@fake.com",
                        "$2b$12$SarrTn1SWbB2/k.JugfBSOgpLIumfkzuSKXlCImDsKghyRHttUxxm")
        email_verification.update_user_verified_in_db("john12@fake.com")
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT verified FROM users WHERE email='john12@fake.com'")
                self.assertTrue(curs.fetchone().verified)

    def test_successful_registration_page_when_correct_token_is_entered(self):
        email_verification.save_token_to_redis("111111", "john12@fake.com")
        with patch("todolists.user_authentication.get_user_id") as get_user_id:
            get_user_id.return_value = "111"
            result = self.simulate_post("/email_verification", params={"token": "111111"})
        template = app.templates_env.get_template("successful_registration.html")
        self.assertEqual(result.text, template.render())

    def test_get_error_page_if_token_entered_is_wrong_or_expired(self):
        email_verification.save_token_to_redis("111111", "john12@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111112"})
        template = app.templates_env.get_template("error.html")
        self.assertEqual(result.text, template.render(error="The code entered is either wrong or expired."))
