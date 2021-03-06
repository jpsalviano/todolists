import bcrypt
from secrets import randbelow
from falcon import HTTP_403, HTTP_409
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from todolists import app, db, email_server, redis_conn

class UserRegistration:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        page = app.templates_env.get_template("index.html")
        resp.text = page.render()

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            validate_user_info(req.params)
            encrypted_password = encrypt_password(req.params["password_1"]).decode()
            save_user_info_to_db(req.get_param("name"), req.get_param("email"), encrypted_password)
            send_email_with_token(req.get_param("email"))   
        except ValidationError as error:
            resp.status = HTTP_403
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error=error.message)
        except db.psycopg2.errors.UniqueViolation as error:
            resp.status = HTTP_409
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error="This email is already in use!\n\
                                               You must sign in with your password to use TodoLists.\
                                               Or you can go back, choose another email and try to sign up again.\
                                               If you are not aware of this registration AND you are sure the email is\
                                               yours, contact us.")
        else:
            resp.unset_cookie("session-token")
            template = app.templates_env.get_template("email_verification.html")
            resp.text = template.render()


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def validate_user_info(user_info):
    validate_name(user_info["name"])
    validate_password(user_info["password_1"], user_info["password_2"])

def validate_name(name):
    if (5 < len(name)) and (len(name) < 41):
        pass
    else:
        raise ValidationError("Name must have 6-40 characters.")
    for char in name:
        if char.isalpha() or char in " ":
            pass
        else:
            raise ValidationError("Name must contain only letters and spaces.")

def validate_password(password_1, password_2):
    if password_1 != password_2:
        raise ValidationError("Passwords do not match!")
    if len(password_1) not in range(6, 31):
        raise ValidationError("Password must be 6-30 characters long.")

def encrypt_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed

def save_user_info_to_db(name, email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"INSERT INTO users (name, email, password) \
                           VALUES (%s, %s, %s)", [name, email, password])

def send_email_with_token(email):
    token = create_token()
    save_token_to_redis(token, email)
    email_message = build_email_message_sending_token(token, email)
    server_connection = email_server.connect_server()
    email_server.send_mail(email, email_message, server_connection)

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
    return app.templates_env.get_template("email_message_sending_code.html").render(token=token)
