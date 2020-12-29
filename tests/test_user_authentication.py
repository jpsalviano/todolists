from unittest.mock import patch

from todolists import app, db, redis_conn, user_authentication, user_registration, email_verification

from falcon import testing, HTTP_401


class TestUserAuthentication(testing.TestCase):
    @classmethod
    def setUpClass(cls):
        #Verified user
        encrypted_password = user_registration.encrypt_password("123abc-").decode()
        user_registration.save_user_info_to_db("John Smith", "john12@fake.com", encrypted_password)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute(f"UPDATE users SET verified=true WHERE email='john12@fake.com'")

        #Unverified user
        encrypted_password = user_registration.encrypt_password("-321cba").decode()
        user_registration.save_user_info_to_db("Clark Kent", "clark6@fake.com", encrypted_password)

    @classmethod
    def tearDownClass(cls):
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("TRUNCATE users;")
        with redis_conn.conn as conn:
            conn.flushall()

    def setUp(self):
        super().setUp()
        self.app = app.create()

    def tearDown(self):
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute(f"UPDATE users SET verified=false WHERE email='clark6@fake.com'")

    def test_check_session_token_returns_user_id_if_cookie_exists(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        doc = user_authentication.get_user_id("john12@fake.com")
        result = self.simulate_post("/login", params=user_auth)
        session_token = result.cookies["session-token"].value
        user_id = user_authentication.check_session_token(session_token)
        self.assertEqual(doc, user_id)

    def test_validate_email_verification_in_db(self):
        email = "john12@fake.com"
        self.assertIsNone(user_authentication.validate_email_verification(email))
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_email_verification("clark6@fake.com")

    def test_set_session_token_after_email_is_verified(self):
        user_registration.save_token_to_redis("111111", "clark6@fake.com")
        user_id = user_authentication.get_user_id("clark6@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111111"})
        session_token = result.cookies["session-token"].value
        self.assertTrue(session_token.isalnum())
        self.assertTrue(len(session_token), 12)
        self.assertEqual(user_id, user_authentication.check_session_token(session_token))

    def test_get_login_page_redirects_to_dashboard_if_valid_token_is_already_set(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        login = self.simulate_post("/login", params=user_auth)
        session_token = login.cookies["session-token"].value
        user_id = user_authentication.check_session_token(session_token)
        result = self.simulate_get("/login", cookies={"session-token": session_token})
        template = app.templates_env.get_template("dashboard.html")
        self.assertEqual(result.text, template.render(user_id=user_id))

    def test_get_authentication_form_page_if_no_session_token_is_set(self):
        doc = app.templates_env.get_template("login.html")
        result = self.simulate_get("/login")
        self.assertEqual(doc.render(), result.text)

    @patch("todolists.user_authentication.validate_password_against_db")
    def test_validate_pass_against_db_is_called_with_submitted_form(self, validate_password_against_db):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        self.simulate_post("/login", params=user_auth)
        validate_password_against_db.assert_called_with("john12@fake.com", "123abc-")

    def test_validate_password_against_db(self):
        email = "john12@fake.com"
        password = "123abc-"
        self.assertTrue(user_authentication.validate_password_against_db(email, password))

    def test_get_user_id_from_db(self):
        id_1 = user_authentication.get_user_id("john12@fake.com")
        id_2 = user_authentication.get_user_id("clark6@fake.com")
        self.assertTrue(int(id_1) + 1 == int(id_2))

    def test_create_session_token_returns_12_char_token(self):
        token = user_authentication.create_session_token()
        self.assertTrue(len(token), 12)
        self.assertTrue(token.isalnum())

    def test_set_session_token_on_redis(self):
        session_token = user_authentication.create_session_token()
        user_id = user_authentication.get_user_id("john12@fake.com")
        user_authentication.set_session_token_on_redis(session_token, user_id)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get(session_token), user_id)

    def test_set_session_token_on_response(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        with patch("todolists.user_authentication.create_session_token") as session_token:
            session_token.return_value = "822c9dfbc77e"
            result = self.simulate_post("/login", params=user_auth)
        self.assertEqual("822c9dfbc77e", result.cookies["session-token"].value)

    def test_check_session_token_raises_auth_error_if_cookie_doesnt_exist(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.check_session_token("822c9dfbc77E")
        self.assertEqual(err.exception.message, "Unauthorized.")

    def test_raise_auth_error_when_user_submits_wrong_email_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_password_against_db("chico@fake.com", "123abc-")
        self.assertEqual(err.exception.message, "The email entered is not registered.")

    def test_raise_auth_error_when_user_submits_wrong_password_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_password_against_db("john12@fake.com", "132acb+")
        self.assertEqual(err.exception.message, "The password entered is wrong!")

    def test_raise_auth_error_when_user_submits_unverified_email_on_login_form(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.validate_email_verification("clark6@fake.com")
        self.assertEqual(err.exception.message, "Your email was not verified.")

    def test_get_401_status_code_when_auth_error_is_raised(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "-123abc-"
        }
        result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(result.status, HTTP_401)

    def test_user_authentication_gets_logout_page_if_cookie_is_set(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        login = self.simulate_post("/login", params=user_auth)
        session_token = login.cookies["session-token"].value
        result = self.simulate_delete("/logout", cookies={"session-token": session_token})
        template = app.templates_env.get_template("logout.html")
        self.assertEqual(result.text, template.render())

    def test_logout_deletes_session_cookie_on_redis(self):
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        login = self.simulate_post("/login", params=user_auth)
        session_token = login.cookies["session-token"].value
        user_id = user_authentication.check_session_token(session_token)
        with redis_conn.conn as conn:
            user_id_on_redis = conn.get(session_token).decode()
        self.assertEqual(user_id, user_id_on_redis)
        logout = self.simulate_delete("/logout")
        

    def test_logout_unsets_session_cookie_on_user_browser(self):
        pass