from falcon import testing, HTTP_200, HTTP_403, HTTP_409
from unittest.mock import patch
import bcrypt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from todolists import app, user_registration, email_server, db, redis_conn


class TestUserRegistration(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()
        def verify_user_in_db(email):
            with db.conn as conn:
                with conn.cursor() as curs:
                    curs.execute(f"UPDATE users SET verified=true WHERE email=%s", (email,))
        self.verify_user_in_db = verify_user_in_db

    def tearDown(self):
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users CASCADE;")

    def test_endpoint_status(self):
        result = self.simulate_get("/register")
        self.assertEqual(result.status, HTTP_200)


    def test_validation_error_status_code(self):
        user_info = {
            "name": "123",
            "email": "john12@fake.com",
            "password_1": "abc123",
            "password_2": "abc1234"
        }

        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(result.status, HTTP_403)

    @patch("todolists.email_server.connect_server")
    @patch("todolists.email_server.send_mail")
    def test_unique_violation_status_code(self, connect_server, send_mail):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc123",
            "password_2": "abc123"
        }
        self.simulate_post("/register", params=user_info)
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(result.status, HTTP_409)

    def test_get_user_form(self):
        result = self.simulate_get("/register")
        template = app.templates_env.get_template("register.html")
        self.assertEqual(result.text, template.render())

    @patch("todolists.email_server.connect_server")
    @patch("todolists.email_server.send_mail")
    def test_submitted_form_is_saved_to_database(self, connect_server, send_mail):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT name FROM users WHERE email = 'john12@fake.com';")
                self.assertEqual("John Smith", curs.fetchone().name)
                curs.execute("SELECT password FROM users WHERE email = 'john12@fake.com';")
                self.assertTrue(bcrypt.checkpw("abc123-".encode(), curs.fetchone().password.encode()))

    def test_raise_exception_if_verified_email_already_in_db(self):
        user_registration.save_user_info_to_db("John Smith", "john12@fake.com", "abc123-")
        self.verify_user_in_db("john12@fake.com")
        with self.assertRaises(db.psycopg2.errors.UniqueViolation) as error:
            user_registration.save_user_info_to_db("John Smith", "john12@fake.com", "abc123-")
        self.assertTrue("users_email_key" in error.exception.diag.message_primary)

    def test_get_error_page_if_verified_email_already_in_db(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Your email is already in use! Please choose another one.")
        user_registration.save_user_info_to_db("John Smith", "john12@fake.com", "abc123-")
        self.verify_user_in_db("john12@fake.com")
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(doc, result.text)

    def test_raise_exception_if_name_contains_not_allowed_characters(self):
        user_info = {
            "name": "@John.Smith 1",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(user_registration.ValidationError) as error:
            user_registration.validate_user_info(user_info)
        self.assertEqual(error.exception.message, "Full name accepts only letters and spaces.")

    def test_get_error_page_if_name_contains_not_allowed_characters(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Full name accepts only letters and spaces.")
        user_info = {
            "name": "John-Smith&",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(doc, result.text)       

    def test_raise_exception_if_passwords_dont_match(self):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "bac123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(user_registration.ValidationError) as error:
            user_registration.validate_user_info(user_info)
        self.assertEqual(error.exception.message, "Passwords do not match!")

    def test_get_error_page_if_passwords_dont_match(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Passwords do not match!")
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc213-"
        }
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(doc, result.text)

    def test_raise_exception_if_password_too_short(self):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc12",
            "password_2": "abc12"
        }
        with self.assertRaises(user_registration.ValidationError) as error:
            user_registration.validate_user_info(user_info)
        self.assertEqual(error.exception.message, "Password must be 6-30 characters long.")

    def test_get_error_page_if_password_too_short(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Password must be 6-30 characters long.")
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": "abc12",
            "password_2": "abc12"
        }
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(doc, result.text)

    def test_raise_exception_if_password_too_long(self):
        user_info = {
            "name": "John Smith",
            "email": "john12@fake.com",
            "password_1": 31*".",
            "password_2": 31*"."
        }
        with self.assertRaises(user_registration.ValidationError) as error:
            user_registration.validate_user_info(user_info)
        self.assertEqual(error.exception.message, "Password must be 6-30 characters long.")

    def test_get_error_page_if_password_too_short(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Password must be 6-30 characters long.")
        user_info = {
            "name": "John Smith",
            "email": "john112@fake.com",
            "password_1": 31*".",
            "password_2": 31*"."
        }
        result = self.simulate_post("/register", params=user_info)
        self.assertEqual(doc, result.text)

    def test_encrypt_password(self):
        password = "abc123-"
        result = user_registration.encrypt_password(password)
        self.assertTrue(bcrypt.checkpw(password.encode(), result))

    def test_create_token_for_user_registration(self):
        token = user_registration.create_token()
        self.assertTrue(len(token), 6)
        self.assertTrue(token.isdecimal())

    def test_save_token_to_redis(self):
        user_registration.save_token_to_redis("111111", "john12@fake.com")
        with redis_conn.conn as conn:
            self.assertTrue(conn.get("111111").decode(), "john12@fake.com")

    def test_build_sending_token_message_html_body(self):
        body = app.templates_env.get_template("email_message_sending_code.html").render(token="111111")
        result = user_registration.build_email_message_sending_token_html_body("111111")
        self.assertEqual(body, result)

    def test_build_sending_token_message_as_mime_str(self):
        message = user_registration.build_email_message_sending_token("john12@fake.com", "111111")
        doc = MIMEMultipart()
        doc['Subject'] = "Finish your registration on TodoLists!"
        doc['From'] = "TodoLists"
        doc['To'] = "john12@fake.com"
        body = user_registration.build_email_message_sending_token_html_body("111111")
        doc.attach(MIMEText(body, "html"))
        self.assertTrue("111111" in doc.as_string())
        self.assertEqual(len(doc.as_string()), len(message))

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

    def test_get_credentials(self):
        with open("EMAIL_", "r") as doc_file:
            doc = doc_file.read().split("\n")
        result = email_server.get_credentials()
        self.assertEqual(doc, result)

    @patch("todolists.email_server.connect_server")
    def test_email_server_is_called_with_user_email(self, connect_server):
        user_registration.send_email_with_token("john12@fake.com")
        connect_server.assert_called_once()

    @patch("todolists.email_server.connect_server")
    @patch("todolists.email_server.send_mail")
    def test_email_server_sends_message_token(self, send_mail, connect_server):
        user_registration.send_email_with_token("john12@fake.com")
        email_server.send_mail.assert_called_once()
