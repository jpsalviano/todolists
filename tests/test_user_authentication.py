from falcon import testing
from unittest.mock import patch

from todolists import app, db, redis_conn, user_authentication


class TestUserAuthentication(testing.TestCase):
    @classmethod
    def setUpClass(cls):
        #Verified user
        encrypted_password = app.user_registration.encrypt_password("123abc-").decode()
        app.user_registration.save_user_to_db("John Smith", "john12@fake.com", encrypted_password)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute(f"UPDATE users SET verified=true WHERE email='john12@fake.com'")

        #Unverified user
        encrypted_password = app.user_registration.encrypt_password("-321cba").decode()
        app.user_registration.save_user_to_db("Clark Kent", "clark6@fake.com", encrypted_password)

    @classmethod
    def tearDownClass(cls):
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")

    def setUp(self):
        super().setUp()
        self.app = app.create()

    def test_get_authentication_form_page(self):
        doc = app.templates_env.get_template("login.html")
        result = self.simulate_get("/login")
        self.assertEqual(doc.render(), result.text)

    @patch("todolists.app.user_authentication.validate_email_password_against_db")
    def test_validate_pass_against_db_is_called_with_submitted_form(self, validate_email_password_against_db):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        self.simulate_post("/login", params=user_auth)
        validate_email_password_against_db.assert_called_with("john12@fake.com", "123abc-")

    def test_validate_email_password_against_db(self):
        email = "john12@fake.com"
        password = "123abc-"
        self.assertTrue(user_authentication.validate_email_password_against_db(email, password))
    
    def test_is_user_email_verified_in_db(self):
        email = "john12@fake.com"
        self.assertTrue(user_authentication.is_user_email_verified(email))

    def test_get_user_id_from_db(self):
        id_1 = user_authentication.get_user_id("john12@fake.com")
        id_2 = user_authentication.get_user_id("clark6@fake.com")
        self.assertTrue(int(id_1) + 1 == int(id_2))

    def test_create_session_cookie_token_returns_12_char_token(self):
        result = user_authentication.create_session_cookie_token()
        self.assertTrue(len(result), 12)

    def test_set_cookie_on_redis(self):
        cookie_value = user_authentication.create_session_cookie_token()
        user_id = user_authentication.get_user_id("john12@fake.com")
        user_authentication.set_cookie_on_redis(cookie_value, user_id)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get(cookie_value), user_id)

    def test_set_cookie_on_response(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        with patch("todolists.user_authentication.create_session_cookie_token") as cookie_value:
            cookie_value.return_value = "822c9dfbc77e"
            result = self.simulate_post("/login", params=user_auth)
        self.assertEqual("822c9dfbc77e", result.cookies["session-token"].value)

    def test_raise_auth_error_when_user_submits_wrong_email_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_email_password_against_db("chico@fake.com", "123abc-")
        self.assertEqual(err.exception.message, "The email entered is not registered.")

    def test_raise_auth_error_when_user_submits_wrong_password_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_email_password_against_db("john12@fake.com", "132acb+")
        self.assertEqual(err.exception.message, "The password entered is wrong!")

    def test_raise_auth_error_when_user_submits_unverified_email_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.is_user_email_verified("clark6@fake.com")
        self.assertEqual(err.exception.message, "Your email was not verified.")

    def test_check_session_cookie_returns_true(self):
        pass
