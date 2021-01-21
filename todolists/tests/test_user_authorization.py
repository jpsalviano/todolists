from secrets import token_hex
from time import sleep

from falcon import testing

from todolists import redis_conn, user_authorization


class TestUserAuthorization(testing.TestCase):

    def setUp(self):
        flushall_from_redis()

    def test_user_authorization_returns_user_id_if_valid_and_authorized_token_is_set(self):
        session_token = token_hex(32)
        set_session_token_on_redis(session_token, "1234")
        result = user_authorization.check_session_token(session_token)
        self.assertEqual(result, "1234")

    def test_user_authorization_raises_error_if_token_set_is_valid_but_wrong(self):
        session_token = token_hex(32)
        set_session_token_on_redis(session_token, "1234")
        with self.assertRaises(user_authorization.AuthorizationError) as error:
            user_authorization.check_session_token(token_hex(32))
        self.assertEqual(error.exception.message, "Wrong/expired token.")

    def test_user_authorization_raises_error_if_token_set_is_valid_but_expired(self):
        session_token = token_hex(32)
        with redis_conn.session_conn as conn:
            conn.set(session_token, "user_id", 1)
            sleep(1)
        with self.assertRaises(user_authorization.AuthorizationError) as error:
            user_authorization.check_session_token(session_token)
        self.assertEqual(error.exception.message, "Wrong/expired token.")

    def test_user_authorization_raises_error_if_bad_token_is_set(self):
        session_token = "<script>I'm a hacker 8-)</script>"
        with self.assertRaises(user_authorization.AuthorizationError) as error:
            user_authorization.check_session_token(session_token)
        self.assertEqual(error.exception.message, "Bad token.")


def set_session_token_on_redis(session_token, user_id):
    with redis_conn.session_conn as conn:
        conn.set(session_token, user_id)

def flushall_from_redis():
    with redis_conn.session_conn as conn:
        conn.flushall()