import bcrypt
from secrets import token_hex

from todolists import app, db, redis_conn

from falcon import HTTP_401


class UserAuthentication:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("dashboard.html")
            resp.body = template.render(user_id=user_id)
        except:
            template = app.templates_env.get_template("login.html")
            resp.body = template.render()

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            session_token = authenticate_user(req.get_param("email"), req.get_param("password"))
        except AuthenticationError as err:
            resp.status = HTTP_401
            resp.body = err.message
        else:
            resp.set_cookie("session-token", session_token)
            user_id = get_user_id(req.get_param("email"))
            template = app.templates_env.get_template("dashboard.html")
            resp.body = template.render(user_id=user_id)

    def on_delete(self, req, resp):
        resp.content_type = "text/html"
        template = app.templates_env.get_template("logout.html")
        resp.body = template.render()


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
