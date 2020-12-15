import bcrypt
from falcon import testing, HTTP_200
from jinja2 import Environment, FileSystemLoader

from todolists import app


class TestUserRegistration(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()
        self.templates_env = Environment(
                             loader=FileSystemLoader('todolists/templates'),
                             autoescape=True,
                             trim_blocks=True,
                             lstrip_blocks=True)

    def tearDown(self):
        with app.db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    def test_endpoint_status(self):
        result = self.simulate_get("/register")
        self.assertEqual(result.status, HTTP_200)

    def test_get_user_form(self):
        result = self.simulate_get("/register")
        template = self.templates_env.get_template("register.html")
        self.assertEqual(result.text, template.render())

    def test_submitted_form_is_saved_to_database(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        result = self.simulate_post("/register", params=user_info)
        with app.db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT email FROM users WHERE username = 'john12';")
                self.assertEqual("john12@fake.com", curs.fetchone().email)

    def test_raise_exception_if_username_already_exists_in_database(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        app.save_user_to_db("john12", "john12@fake.com", "abc123-")
        with self.assertRaises(app.psycopg2.errors.UniqueViolation) as err:
            app.save_user_to_db("john12", "john12@fake.com", "abc123-")
        self.assertTrue("users_username_key" in err.exception.diag.message_primary)

    def test_raise_exception_if_email_already_exists_in_database(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        app.save_user_to_db("john12", "john12@fake.com", "abc123-")
        with self.assertRaises(app.psycopg2.errors.UniqueViolation) as err:
            app.save_user_to_db("john21", "john12@fake.com", "abc123-")
        self.assertTrue("users_email_key" in err.exception.diag.message_primary)

    def test_raise_exception_if_username_too_short(self):
        user_info = {
            "username": "john1",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Username must be 6-30 characters long.")

    def test_raise_exception_if_username_too_long(self):
        user_info = {
            "username": 31*"a",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Username must be 6-30 characters long.")

    def test_raise_exception_if_username_contains_not_allowed_characters(self):
        user_info = {
            "username": "john.12",
            "email": "john12@fake.com",
            "password_1": "abc123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Username must contain letters and numbers only.")

    def test_raise_exception_if_passwords_dont_match(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "bac123-",
            "password_2": "abc123-"
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Passwords do not match!")

    def test_raise_exception_if_password_too_short(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": "abc12",
            "password_2": "abc12"
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Password must be 6-30 characters long.")

    def test_raise_exception_if_password_too_long(self):
        user_info = {
            "username": "john12",
            "email": "john12@fake.com",
            "password_1": 31*".",
            "password_2": 31*"."
        }
        with self.assertRaises(app.ValidationError) as err:
            app.validate_user_info(user_info)
        self.assertEqual(err.exception.message, "Password must be 6-30 characters long.")

    def test_encrypt_password(self):
        password = "abc123-"
        result = app.encrypt_password(password)
        self.assertTrue(bcrypt.checkpw(password.encode(), result))

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
