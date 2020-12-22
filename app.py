import falcon
from jinja2 import Environment, FileSystemLoader

from todolists import db, user_registration, email_verification, user_authentication


templates_env = Environment(
                loader=FileSystemLoader('todolists/templates'),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True)


class UserRegistration:
    def on_get(self, req, resp):
        content_type = "text/html"
        page = templates_env.get_template("register.html")
        resp.body = page.render()

    def on_post(self, req, resp):
        content_type = "text/html"
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
        content_type = "text/html"
        try:
            email = email_verification.get_email_by_token(req.get_param("token"))
            email_verification.update_user_verified_in_db(email)
        except user_registration.ValidationError as err:
            template = templates_env.get_template("error.html")
            resp.body = template.render(error=err)
        else:
            template = templates_env.get_template("successful_registration.html")
            resp.body = template.render()


class UserAuthentication:
    def on_get(self, req, resp):
        content_type = "text/html"
        template = templates_env.get_template("login.html")
        resp.body = template.render()

    def on_post(self, req, resp):
        content_type = "text/html"
        try:
            user_authentication.validate_password_against_db(req.get_param("email"), req.get_param("password"))
            user_authentication.is_verified(req.get_param("email"))
            cookie_key = user_authentication.create_cookie_key_token()
            cookie_value = user_authentication.get_user_id(req.get_param("email"))
            user_authentication.set_key_value_cookie_on_redis(cookie_key, cookie_value)
            resp.set_cookie(cookie_key, cookie_value)
        except:
            raise Exception


def create():
    app = falcon.API()
    app.req_options.auto_parse_form_urlencoded = True
    app.resp_options.secure_cookies_by_default = False
    app.add_route("/register", UserRegistration())
    app.add_route("/email_verification", EmailVerification())
    app.add_route("/login", UserAuthentication())
    return app

app = create()