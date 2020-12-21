import bcrypt
from secrets import token_hex

from todolists import db


def validate_password_against_db(email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT password FROM users WHERE email = %s", [email])
            hashed = curs.fetchone().password
    return bcrypt.checkpw(password.encode(), hashed.encode())

def check_verified_bool_in_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT verified FROM users WHERE email = %s", [email])
            return curs.fetchone().verified

def get_user_id_from_database(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return curs.fetchone().user_id

def create_cookie_key_token():
    return token_hex(6)