import bcrypt
from jinja2 import Environment, FileSystemLoader
import falcon
import psycopg2
from secrets import randbelow
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from todolists import db, redis_conn, email_server


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
        resp.content_type = "text/html"
        try:
            validate_user_info(req.params)
            encrypted_password = encrypt_password(req.params["password_1"]).decode()
            save_user_to_db(req.get_param("username"), req.get_param("email"), encrypted_password)
            send_email_with_token(req.get_param("email"))
        except ValidationError as err:
            resp.body = err.exception.message
        except psycopg2.errors.UniqueViolation as err:
            resp.body = err.diag.message_primary
        else:
            template = templates_env.get_template("email_verification.html")
            resp.body = template.render()


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


class EmailVerification:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        update_user_verified_in_db(get_email(req.get_param("token")))
        template = templates_env.get_template("successful_registration.html")
        resp.body = template.render()

def create_token():
        token = randbelow(1000000)
        return "{:06d}".format(token)

def save_token_to_redis(token, email):
    with redis_conn.conn as conn:
        conn.set(token, email)
        conn.expire(token, 600)

def build_email_message_sending_token(token, email):
    message = MIMEMultipart()
    message['Subject'] = "Finish your registration on TodoLists!"
    message['From'] = "TodoLists"
    message['To'] = email
    body = build_email_message_sending_token_html_body(token)
    message.attach(MIMEText(body, "html"))
    return message.as_string()

def build_email_message_sending_token_html_body(token):
    return templates_env.get_template("email_message_sending_code.html").render(token=token)

def send_email_with_token(email):
    token = create_token()
    save_token_to_redis(token, email)
    email_message = build_email_message_sending_token(token, email)
    server_connection = email_server.connect_server()
    email_server.send_mail(email, email_message, server_connection)

def get_email(token):
    with redis_conn.conn as conn:
        email = conn.get(token)
    return email.decode()

def update_user_verified_in_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"UPDATE users SET verified=true WHERE email='{email}'")


def create():
    app = falcon.API()
    app.add_route("/register", UserRegistration())
    app.add_route("/email_verification", EmailVerification())
    app.req_options.auto_parse_form_urlencoded = True
    return app

app = create()