from falcon import testing, HTTP_403
from time import sleep

from todolists import app, email_verification, user_registration, db, redis_conn



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

    def test_email_verification_gets_email_value_from_redis(self):
        encrypted_password = user_registration.encrypt_password("-321cba").decode()
        user_registration.save_user_info_to_db("Clark Kent", "clark6@fake.com", encrypted_password)
        user_registration.save_token_to_redis("111111", "clark6@fake.com")
        self.assertEqual(email_verification.get_email_by_token("111111"), "clark6@fake.com")

    def test_update_user_verified_in_db(self):
        user_registration.save_user_info_to_db("John", "john12@fake.com",
                        "$2b$12$SarrTn1SWbB2/k.JugfBSOgpLIumfkzuSKXlCImDsKghyRHttUxxm")
        email_verification.update_user_verified_in_db("john12@fake.com")
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT verified FROM users WHERE email='john12@fake.com'")
                self.assertTrue(curs.fetchone().verified)

    def test_create_session_token_returns_64_char_token(self):
        token = email_verification.create_session_token()
        self.assertEqual(len(token), 64)
        self.assertTrue(token.isalnum())

    def test_get_user_id_from_db(self):
        #Verified user
        encrypted_password = app.user_registration.encrypt_password("123abc-").decode()
        app.user_registration.save_user_info_to_db("John Smith", "john12@fake.com", encrypted_password)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute(f"UPDATE users SET verified=true WHERE email='john12@fake.com'")

        #Unverified user
        encrypted_password = app.user_registration.encrypt_password("-321cba").decode()
        app.user_registration.save_user_info_to_db("Clark Kent", "clark6@fake.com", encrypted_password)

        id_1 = email_verification.get_user_id("john12@fake.com")
        id_2 = email_verification.get_user_id("clark6@fake.com")
        self.assertTrue(int(id_1) + 1 == int(id_2))

    def test_set_session_token_on_redis(self):
        user_registration.save_user_info_to_db("John", "john12@fake.com",
                        "$2b$12$SarrTn1SWbB2/k.JugfBSOgpLIumfkzuSKXlCImDsKghyRHttUxxm")
        session_token = email_verification.create_session_token()
        user_id = email_verification.get_user_id("john12@fake.com")
        email_verification.set_session_token_on_redis(session_token, user_id)
        with redis_conn.conn as conn:
            self.assertTrue(conn.get(session_token), user_id)

    def test_set_session_token_on_response_after_email_is_verified(self):
        encrypted_password = app.user_registration.encrypt_password("-321cba").decode()
        app.user_registration.save_user_info_to_db("Clark Kent", "clark6@fake.com", encrypted_password)
        user_registration.save_token_to_redis("111111", "clark6@fake.com")
        user_id = email_verification.get_user_id("clark6@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111111"})
        session_token = result.cookies["session-token"].value
        self.assertTrue(session_token.isalnum())
        self.assertEqual(len(session_token), 64)

    def test_successful_registration_page_when_correct_token_is_entered(self):
        user_registration.save_user_info_to_db("John", "john12@fake.com",
                        "$2b$12$SarrTn1SWbB2/k.JugfBSOgpLIumfkzuSKXlCImDsKghyRHttUxxm")
        user_registration.save_token_to_redis("111111", "john12@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111111"})
        template = app.templates_env.get_template("successful_registration.html")
        self.assertEqual(result.text, template.render())

    def test_get_error_page_and_403_status_code_when_token_entered_is_expired(self):
        with redis_conn.conn as conn:
            conn.set("111111", "john12@fake.com")
            conn.expire("111111", 1)
        sleep(1)
        result = self.simulate_post("/email_verification", params={"token": "111111"})
        template = app.templates_env.get_template("error.html")
        self.assertEqual(result.text, template.render(error="The code entered is either wrong or expired."))
        self.assertEqual(result.status, HTTP_403)

    def test_get_error_page_and_403_status_code_when_token_entered_is_wrong(self):
        user_registration.save_token_to_redis("111111", "john12@fake.com")
        result = self.simulate_post("/email_verification", params={"token": "111112"})
        template = app.templates_env.get_template("error.html")
        self.assertEqual(result.text, template.render(error="The code entered is either wrong or expired."))
        self.assertEqual(result.status, HTTP_403)
