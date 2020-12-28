import bcrypt
from secrets import token_hex

from todolists import db, redis_conn


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


def authenticate_user(email, password):
    validate_password_against_db(email, password)
    validate_email_verification(email)
    user_id = get_user_id(email)
    session_token = create_session_token()
    set_session_token_on_redis(session_token, user_id)
    return session_token

def validate_password_against_db(email, password):
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

def validate_email_verification(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT verified FROM users WHERE email = %s", [email])
            verified = curs.fetchone().verified
            print(email, verified)
            if verified == True:
                pass
            else:
                raise AuthenticationError("Your email was not verified.")

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def create_session_token():
    return token_hex(6)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.conn as conn:
        conn.set(session_token, user_id)

def check_session_token(session_token):
    with redis_conn.conn as conn:
        user_id = conn.get(session_token)
        if user_id:
            return user_id.decode()
        else:
            raise AuthenticationError("Unauthorized.")
