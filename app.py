import falcon
from falcon import HTTP_401
from jinja2 import Environment, FileSystemLoader

from todolists import db, user_registration, email_verification, user_authentication


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
            user_registration.validate_user_info(req.params)
            encrypted_password = user_registration.encrypt_password(req.params["password_1"]).decode()
            user_registration.save_user_to_db(req.get_param("name"), req.get_param("email"), encrypted_password)
            email_verification.send_email_with_token(req.get_param("email"))   
        except user_registration.ValidationError as err:
            template = templates_env.get_template("error.html")
            resp.body = template.render(error=err.message)
        except db.psycopg2.errors.UniqueViolation as err:
            template = templates_env.get_template("error.html")
            resp.body = template.render(error="Your email is already in use! Please choose another one.")
        else:
            template = templates_env.get_template("email_verification.html")
            resp.body = template.render()


class EmailVerification:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            email = email_verification.get_email_by_token(req.get_param("token"))
            email_verification.update_user_verified_in_db(email)
        except user_registration.ValidationError as err:
            template = templates_env.get_template("error.html")
            resp.body = template.render(error=err)
        else:
            session_token = user_authentication.create_session_token()
            user_id = user_authentication.get_user_id(email)
            user_authentication.set_session_token_on_redis(session_token, user_id)
            resp.set_cookie("session-token", session_token)
            template = templates_env.get_template("successful_registration.html")
            resp.body = template.render()


class UserAuthentication:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = user_authentication.check_session_token(req.cookies)
            template = templates_env.get_template("dashboard.html")
            resp.body = template.render(user_id=user_id)
        except:
            template = templates_env.get_template("login.html")
            resp.body = template.render()

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            session_token = user_authentication.authenticate_user(req.get_param("email"), req.get_param("password"))
        except user_authentication.AuthenticationError as err:
            resp.status = HTTP_401
            resp.body = err.message
        else:
            resp.set_cookie("session-token", session_token)
            user_id = user_authentication.get_user_id(req.get_param("email"))
            template = templates_env.get_template("dashboard.html")
            resp.body = template.render(user_id=user_id)


def create():
    app = falcon.API()
    app.req_options.auto_parse_form_urlencoded = True
    app.resp_options.secure_cookies_by_default = False
    app.add_route("/register", UserRegistration())
    app.add_route("/email_verification", EmailVerification())
    app.add_route("/login", UserAuthentication())
    return app

app = create()