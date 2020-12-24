import bcrypt
from secrets import token_hex

from todolists import db, redis_conn


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


def authenticate(email, password):
    validate_email_password_against_db(email, password)
    is_user_email_verified(email)
    user_id = get_user_id(email)
    cookie_value = create_session_cookie_token()
    set_cookie_on_redis(cookie_value, user_id)
    return cookie_value

def validate_email_password_against_db(email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT password FROM users WHERE email = %s", [email])
            try:
                hashed = curs.fetchone().password
            except:
                raise AuthenticationError("The email entered is not registered.")
    if bcrypt.checkpw(password.encode(), hashed.encode()):
        return True
    else:
        raise AuthenticationError("The password entered is wrong!")
        

def is_user_email_verified(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT verified FROM users WHERE email = %s", [email])
            if curs.fetchone().verified:
                return True
            else:
                raise AuthenticationError("Your email was not verified.")

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def create_session_cookie_token():
    return token_hex(6)

def set_cookie_on_redis(name, value):
    with redis_conn.conn as conn:
        conn.set(name, value)