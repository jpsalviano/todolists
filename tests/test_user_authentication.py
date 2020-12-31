from unittest.mock import patch

from todolists import app, db, redis_conn, user_authentication, user_registration, email_verification

from falcon import testing, HTTP_401


class TestUserAuthenticationWithoutPreviousSessionTokenSet(testing.TestCase):

    def setUp(self):
        super().setUp()
        self.app = app.create()

    def tearDown(self):
        truncate_users()
        flushall_from_redis()

    def test_on_get_user_authentication_renders_form_page(self):
        doc = app.templates_env.get_template("login.html")
        result = self.simulate_get("/login")
        self.assertEqual(doc.render(), result.text)

    @patch("todolists.user_authentication.authenticate_user")
    def test_on_post_authenticate_user_is_called_with_submitted_form(self, authenticate_user):
        add_verified_user()
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        self.simulate_post("/login", params=user_auth)
        authenticate_user.assert_called_with("john12@fake.com", "123abc-")
        
    def test_validate_email_verification_status_on_db(self):
        add_verified_user()
        with db.conn as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute("SELECT verified, password FROM users WHERE email = 'john12@fake.com'")
                    user = curs.fetchone()
                    email_verification = user.verified
                    stored_password = user.password
                except:
                    email_verification = None
                    stored_password = None
        self.assertIsNone(user_authentication.validate_email_verification(email_verification))
        add_unverified_user()
        with db.conn as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute("SELECT verified, password FROM users WHERE email = 'clark6@fake.com'")
                    user = curs.fetchone()
                    email_verification = user.verified
                    stored_password = user.password
                except:
                    email_verification = None
                    stored_password = None
        with self.assertRaises(user_authentication.AuthenticationError) as error:
            user_authentication.validate_email_verification(email_verification)
        self.assertEqual(error.exception.message, "Your email hasn't been verified.")
        with db.conn as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute("SELECT verified, password FROM users WHERE email = 'jackson5@fake.com'")
                    user = curs.fetchone()
                    email_verification = user.verified
                    stored_password = user.password
                except:
                    email_verification = None
                    stored_password = None
        with self.assertRaises(user_authentication.AuthenticationError) as error:
            user_authentication.validate_email_verification(email_verification)
        self.assertEqual(error.exception.message, "The email entered is not registered.")

    def test_validate_password_against_stored_on_db(self):
        add_verified_user()
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT password FROM users WHERE email = 'john12@fake.com'")
                stored_password = curs.fetchone().password
        password = "123abc-"
        self.assertIsNone(user_authentication.validate_password_against_db(password, stored_password))
        
    def test_get_user_id_by_user_email_from_db(self):
        add_verified_user()
        add_unverified_user()
        id_1 = user_authentication.get_user_id("john12@fake.com")
        id_2 = user_authentication.get_user_id("clark6@fake.com")
        self.assertTrue(int(id_1) + 1 == int(id_2))

    def test_create_session_token_returns_64_char_token(self):
        session_token = user_authentication.create_session_token()
        self.assertEqual(len(session_token), 64)
        self.assertTrue(session_token.isalnum())

    def test_set_session_token_on_redis(self):
        add_verified_user()
        session_token = user_authentication.create_session_token()
        user_id = user_authentication.get_user_id("john12@fake.com")
        user_authentication.set_session_token_on_redis(session_token, user_id)
        with redis_conn.conn as conn:
            self.assertEqual(conn.get(session_token).decode(), user_id)

    def test_authenticate_user_returns_session_token(self):
        add_verified_user()
        session_token = user_authentication.authenticate_user("john12@fake.com", "123abc-")
        self.assertEqual(len(session_token), 64)
        self.assertTrue(session_token.isalnum())

    def test_on_post_user_authentication_sets_session_token_on_response(self):
        add_verified_user()
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        session_token = user_authentication.create_session_token()
        with patch("todolists.user_authentication.create_session_token") as create_session_token:
            create_session_token.return_value = session_token
            result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(session_token, result.cookies["session-token"].value)

    def test_on_post_correct_user_auth_user_authentication_renders_dashboard(self):
        add_verified_user()
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        doc = app.templates_env.get_template("dashboard.html")
        user_id = user_authentication.get_user_id("john12@fake.com")
        result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(doc.render(user_id=user_id), result.text)

    def test_user_authentication_renders_error_page_when_unregistered_email_submitted_on_login_form(self):
        user_auth = {
            "email": "chico15@fake.com",
            "password": "123abc-"
        }
        doc = app.templates_env.get_template("error.html")
        error = user_authentication.AuthenticationError("The email entered is not registered.")
        result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(doc.render(error=error), result.text)

    def test_user_authentication_renders_error_page_when_unverified_email_submitted_on_login_form(self):
        add_unverified_user()
        user_auth = {
            "email": "clark6@fake.com",
            "password": "-321cba"
        }
        doc = app.templates_env.get_template("error.html")
        error = user_authentication.AuthenticationError("Your email hasn't been verified.")
        result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(doc.render(error=error), result.text)

    def test_user_authentication_renders_error_page_when_wrong_password_submitted_on_login_form(self):
        add_verified_user()
        user_auth = {
            "email": "john12@fake.com",
            "password": "-321cba"
        }
        doc = app.templates_env.get_template("error.html")
        error = user_authentication.AuthenticationError("The password entered is wrong!")
        result = self.simulate_post("/login", params=user_auth)
        self.assertEqual(doc.render(error=error), result.text)
        
'''    def test_check_session_token_returns_user_id_if_cookie_exists(self):
        add_verified_user()
        user_auth = {
            "email": "john12@fake.com",
            "password": "123abc-"
        }
        doc = user_authentication.get_user_id("john12@fake.com")
        result = self.simulate_post("/login", params=user_auth)
        session_token = result.cookies["session-token"].value
        user_id = user_authentication.check_session_token(session_token)
        self.assertEqual(doc, user_id)

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



    def test_check_session_token_raises_auth_error_if_cookie_doesnt_exist(self):
        with self.assertRaises(user_authentication.AuthenticationError) as err:
            user_authentication.check_session_token("822c9dfbc77E")
        self.assertEqual(err.exception.message, "Unauthorized.")

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
        pass'''


def add_verified_user():
    encrypted_password = user_registration.encrypt_password("123abc-").decode()
    user_registration.save_user_info_to_db("John Smith", "john12@fake.com", encrypted_password)
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"UPDATE users SET verified=true WHERE email='john12@fake.com'")

def add_unverified_user():
    encrypted_password = user_registration.encrypt_password("-321cba").decode()
    user_registration.save_user_info_to_db("Clark Kent", "clark6@fake.com", encrypted_password)

def truncate_users():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE users;")

def flushall_from_redis():
    with redis_conn.conn as conn:
        conn.flushall()