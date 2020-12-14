import bcrypt
from jinja2 import Environment, FileSystemLoader
import falcon
from todolists import db


templates_env = Environment(
                loader=FileSystemLoader('todolists/templates'),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True)


class UserRegistration:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        page = templates_env.get_template("register.html")
        resp.body = page.render()

    def on_post(self, req, resp):
        try:
            validate_user_info(req.params)
            encrypted_password = encrypt_password(req.params["password_1"]).decode()
            save_user_to_db(req.get_param("username"), req.get_param("email"), encrypted_password)
            resp.media = req.params
        except ValidationError as err:
            resp.body = err


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def validate_user_info(user_info):
    validate_username(user_info["username"])
    validate_password(user_info["password_1"], user_info["password_2"])

def validate_username(username):
    if len(username) not in range(6, 31):
        raise ValidationError("Username must be 6-30 characters long.")
    for char in username:
        if not char.isalnum():
            raise ValidationError("Username must contain letters and numbers only.")

def validate_password(password_1, password_2):
    if password_1 != password_2:
        raise ValidationError("Passwords do not match!")
    if len(password_1) not in range(6, 31):
        raise ValidationError("Password must be 6-30 characters long.")

def encrypt_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed

def save_user_to_db(username, email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"INSERT INTO users (username, email, password) \
                           VALUES ('{username}', '{email}', '{password}')")


def create():
    app = falcon.API()
    app.add_route("/register", UserRegistration())
    app.req_options.auto_parse_form_urlencoded = True
    return app

app = create()