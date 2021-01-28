import falcon
from secrets import randbelow, token_hex
import bcrypt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from todolists import app, redis_conn, db, email_server


class EmailVerification:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            email = get_email_by_token(req.get_param("token"))
            update_user_verified_in_db(email)
        except EmailVerificationError:
            resp.status = falcon.HTTP_403
            template = app.templates_env.get_template("error-wrong-email-token.html")
            resp.text = template.render()
        except:
            resp.status = falcon.HTTP_500
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error="Unexpected error.")
        else:
            session_token = create_session_token()
            user_id = get_user_id(email)
            set_session_token_on_redis(session_token, user_id)
            resp.set_cookie("session-token", session_token)
            template = app.templates_env.get_template("successful_registration.html")
            resp.text = template.render()


class EmailReverification:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            email = req.get_param("email")
            send_email_with_token(email)
            template = app.templates_env.get_template("email_verification.html")
            resp.text = template.render()
        except:
            resp.status = falcon.HTTP_500
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error="Unexpected error.")


class EmailVerificationError(Exception):
    def __init__(self, message):
        self.message = message


def get_email_by_token(token):
    with redis_conn.conn as conn:
        email = conn.get(token)
    if email:
        return email.decode()
    else:
        raise EmailVerificationError("The code entered is either wrong or expired. Go back.")

def update_user_verified_in_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"UPDATE users SET verified=true WHERE email=%s", (email,))

def delete_email_from_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"DELETE DATA FROM users WHERE verified = false AND email = %s", (email,))

def create_session_token():
    return token_hex(32)

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.session_conn as conn:
        conn.set(session_token, user_id)

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
