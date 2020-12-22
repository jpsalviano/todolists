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

    @patch("todolists.app.user_authentication.validate_password_against_db")
    def test_validate_password_against_db_is_called_with_submitted_args(self, validate_password_against_db):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        self.simulate_post("/login", params=user_auth)
        validate_password_against_db.assert_called_with("john12@fake.com", "123abc-")

    def test_validate_password_against_db(self):
        email = "john12@fake.com"
        right_pass = "123abc-"
        wrong_pass = "-cba321"
        self.assertFalse(user_authentication.validate_password_against_db(email, wrong_pass))
        self.assertTrue(user_authentication.validate_password_against_db(email, right_pass))
    
    def test_user_is_verified_in_db(self):
        email_1 = "john12@fake.com"
        email_2 = "clark6@fake.com"
        self.assertTrue(user_authentication.is_verified(email_1))
        self.assertFalse(user_authentication.is_verified(email_2))

    def test_get_user_id_from_db(self):
        id_1 = user_authentication.get_user_id("john12@fake.com")
        id_2 = user_authentication.get_user_id("clark6@fake.com")
        self.assertTrue(int(id_1) + 1 == int(id_2))

    def test_create_cookie_key_token_returns_12_char_token(self):
        result = user_authentication.create_cookie_key_token()
        self.assertTrue(len(result), 12)

    def test_set_key_value_cookie_on_redis(self):
        key = user_authentication.create_cookie_key_token()
        value = user_authentication.get_user_id("john12@fake.com")
        user_authentication.set_key_value_cookie_on_redis(key, value)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get(key), value)

    def test_response_sets_cookie(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        cookie_value = user_authentication.get_user_id("john12@fake.com")
        result = self.simulate_post("/login", params=user_auth)
        cookie_key = list(result.cookies.keys())[0]
        self.assertEqual(cookie_value, result.cookies[cookie_key].value)