from string import hexdigits
from binascii import unhexlify

from todolists import redis_conn


class AuthorizationError(Exception):
    def __init__(self, message):
        self.message = message


def is_64_chars_hex(session_token):
    if len(session_token) == 64:
        for char in session_token:
            char in hexdigits
    else:
        raise AuthorizationError("Bad token.")

def check_session_token(session_token):
    is_64_chars_hex(session_token)
    with redis_conn.session_conn as conn:
        user_id = conn.get(session_token)
        if user_id:
            return user_id.decode()
        else:
            raise AuthorizationError("Wrong/expired token.")
