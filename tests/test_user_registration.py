import bcrypt
from unittest.mock import patch
from falcon import testing, HTTP_200

from todolists import app, db, user_registration


class TestUserRegistration(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()
        def verify_email_in_db(email):
            with db.conn as conn:
                with conn.cursor() as curs:
                    curs.execute(f"UPDATE users SET verified=true WHERE email=%s", (email,))
        self.verify_email_in_db = verify_email_in_db

    def tearDown(self):
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    def test_endpoint_status(self):
        result = self.simulate_get("/register")
        self.assertEqual(result.status, HTTP_200)

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
                curs.execute("SELECT email FROM users WHERE name = 'John Smith';")
                self.assertEqual("john12@fake.com", curs.fetchone().email)

    def test_raise_exception_if_verified_email_already_in_db(self):
        user_registration.save_user_to_db("John Smith", "john12@fake.com", "abc123-")
        self.verify_email_in_db("john12@fake.com")
        with self.assertRaises(db.psycopg2.errors.UniqueViolation) as err:
            user_registration.save_user_to_db("John Smith", "john12@fake.com", "abc123-")
        self.assertTrue("users_email_key" in err.exception.diag.message_primary)

    def test_get_error_page_if_verified_email_already_in_db(self):
        template = app.templates_env.get_template("error.html")
        doc = template.render(error="Your email is already in use! Please choose another one.")
        user_registration.save_user_to_db("John Smith", "john12@fake.com", "abc123-")
        self.verify_email_in_db("john12@fake.com")
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
        with self.assertRaises(user_registration.ValidationError) as err:
            user_registration.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Full name accepts only letters and spaces.")

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
        with self.assertRaises(user_registration.ValidationError) as err:
            user_registration.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Passwords do not match!")

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
        with self.assertRaises(user_registration.ValidationError) as err:
            user_registration.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Password must be 6-30 characters long.")

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
        with self.assertRaises(user_registration.ValidationError) as err:
            user_registration.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Password must be 6-30 characters long.")

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
