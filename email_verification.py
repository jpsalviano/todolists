from falcon import HTTP_403
from secrets import token_hex

from todolists import app, redis_conn, db


class EmailVerification:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            email = get_email_by_token(req.get_param("token"))
            update_user_verified_in_db(email)
        except ValidationError as err:
            resp.status = HTTP_403
            template = app.templates_env.get_template("error.html")
            resp.body = template.render(error=err)
        else:
            session_token = create_session_token()
            user_id = get_user_id(email)
            set_session_token_on_redis(session_token, user_id)
            resp.set_cookie("session-token", session_token)
            template = app.templates_env.get_template("successful_registration.html")
            resp.body = template.render()


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def get_email_by_token(token):
    with redis_conn.conn as conn:
        email = conn.get(token)
    if email:
        return email.decode()
    else:
        raise ValidationError("The code entered is either wrong or expired.")

def update_user_verified_in_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"UPDATE users SET verified=true WHERE email=%s", (email,))

def create_session_token():
    return token_hex(6)

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.conn as conn:
        conn.set(session_token, user_id)