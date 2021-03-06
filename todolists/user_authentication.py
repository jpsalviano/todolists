import bcrypt
from secrets import token_hex

from todolists import app, db, redis_conn
from todolists.user_authorization import check_session_token, AuthorizationError

import falcon


class UserAuthentication:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("successful_login.html")
            resp.text = template.render()
        except:
            resp.status = falcon.HTTP_401
            template = app.templates_env.get_template("login.html")
            resp.text = template.render()

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            session_token = authenticate_user(req.get_param("email"), req.get_param("password"))
        except NotVerifiedEmail as error:
            try:
                stored_password = get_stored_password_by_email(req.get_param("email"))
                validate_password_against_db(req.get_param("password"), stored_password)
                template = app.templates_env.get_template("error-email-not-verified.html")
                resp.text = template.render(email=req.get_param("email"))
            except AuthenticationError as error:
                resp.status = falcon.HTTP_401
                template = app.templates_env.get_template("error.html")
                resp.text = template.render(error=error)
        except:
            resp.status = falcon.HTTP_500
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error="Unknown error.")
        else:
            resp.set_cookie("session-token", session_token)
            user_id = get_user_id(req.get_param("email"))
            template = app.templates_env.get_template("successful_login.html")
            resp.text = template.render()


class UserLogout:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            check_session_token(req.cookies["session-token"])
            unset_session_token_on_redis(req.cookies["session-token"])
            resp.unset_cookie("session-token")
            template = app.templates_env.get_template("logout.html")
            resp.text = template.render()
        except AuthorizationError:
            resp.status = falcon.HTTP_401
            resp.unset_cookie("session-token")
            template = app.templates_env.get_template("index.html")
            resp.text = template.render()

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            check_session_token(req.cookies["session-token"])
            unset_session_token_on_redis(req.cookies["session-token"])
            resp.unset_cookie("session-token")
            template = app.templates_env.get_template("logout.html")
            resp.text = template.render()
        except AuthorizationError:
            resp.status = falcon.HTTP_401
            resp.unset_cookie("session-token")
            template = app.templates_env.get_template("index.html")
            resp.text = template.render()


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


class NotVerifiedEmail(Exception):
    def __init__(self, message):
        self.message = message


def authenticate_user(email, password):
    with db.conn as conn:
        with conn.cursor() as curs:
            try:
                curs.execute("SELECT verified, password FROM users WHERE email = %s", [email])
                user = curs.fetchone()
                email_verification = user.verified
                stored_password = user.password
            except:
                email_verification = None
                stored_password = None
    validate_email_verification(email_verification)
    validate_password_against_db(password, stored_password)
    user_id = get_user_id(email)
    session_token = create_session_token()
    set_session_token_on_redis(session_token, user_id)
    return session_token

def validate_email_verification(email_verification):
    if email_verification == None:
        raise AuthenticationError("The email entered is not registered.")
    if email_verification == False:
        raise NotVerifiedEmail("Your email was not verified.")

def validate_password_against_db(password, stored_password):
    hashed = stored_password
    if not bcrypt.checkpw(password.encode(), hashed.encode()):
        raise AuthenticationError("The password entered is wrong!")

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def get_stored_password_by_email(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT password FROM users WHERE email = %s", [email])
            return str(curs.fetchone().password)

def create_session_token():
    return token_hex(32)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.session_conn as conn:
        conn.set(session_token, user_id)

def unset_session_token_on_redis(session_token):
    with redis_conn.session_conn as conn:
        return conn.delete(session_token)
