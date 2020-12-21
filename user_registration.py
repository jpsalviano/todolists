import bcrypt

from todolists import db


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def validate_user_info(user_info):
    validate_name(user_info["name"])
    validate_password(user_info["password_1"], user_info["password_2"])

def validate_name(name):
    for char in name:
        if char.isalpha() or char in " ":
            pass
        else:
            raise ValidationError(f"Full name accepts only letters and spaces.")

def validate_password(password_1, password_2):
    if password_1 != password_2:
        raise ValidationError("Passwords do not match!")
    if len(password_1) not in range(6, 31):
        raise ValidationError("Password must be 6-30 characters long.")

def encrypt_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed

def save_user_to_db(name, email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"INSERT INTO users (name, email, password) \
                           VALUES (%s, %s, %s)", [name, email, password])