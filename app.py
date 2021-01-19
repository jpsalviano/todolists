import falcon
from jinja2 import Environment, FileSystemLoader

from todolists import db, user_registration, email_verification, user_authentication, user_dashboard


templates_env = Environment(
                loader=FileSystemLoader('todolists/templates'),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True)


def create():
    app = falcon.App()
    app.req_options.auto_parse_form_urlencoded = True
    app.resp_options.secure_cookies_by_default = False
    app.add_route("/", user_authentication.UserAuthentication())
    app.add_route("/register", user_registration.UserRegistration())
    app.add_route("/email_verification", email_verification.EmailVerification())
    app.add_route("/login", user_authentication.UserAuthentication())
    app.add_route("/logout", user_authentication.UserLogout())
    app.add_route("/dashboard", user_dashboard.UserDashboard())
    app.add_route("/create-todolist", user_dashboard.CreateTodolist())
    app.add_route("/get-todolist", user_dashboard.ReadTodoList())
    app.add_route("/update-todolist", user_dashboard.UpdateTodoList())
    app.add_route("/delete-todolist", user_dashboard.DeleteTodoList())
    app.add_route("/create-task", user_dashboard.CreateTask())
    app.add_route("/update-task", user_dashboard.UpdateTask())
    return app

app = create()