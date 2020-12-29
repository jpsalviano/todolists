import falcon
from falcon import HTTP_401
from jinja2 import Environment, FileSystemLoader

from todolists import db, user_registration, email_verification, user_authentication


templates_env = Environment(
                loader=FileSystemLoader('todolists/templates'),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True)


def create():
    app = falcon.API()
    app.req_options.auto_parse_form_urlencoded = True
    app.resp_options.secure_cookies_by_default = False
    app.add_route("/register", user_registration.UserRegistration())
    app.add_route("/email_verification", email_verification.EmailVerification())
    app.add_route("/login", user_authentication.UserAuthentication())
    app.add_route("/logout", user_authentication.UserAuthentication())
    return app

app = create()