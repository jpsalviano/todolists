from pathlib import Path

import falcon
from jinja2 import Environment, FileSystemLoader

from todolists import db, user_registration, email_verification, user_authentication, user_dashboard, user_todolists, user_tasks


templates_env = Environment(
                loader=FileSystemLoader('todolists/templates'),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True)


class Index:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        template = templates_env.get_template("index.html")
        resp.text = template.render()


def create():
    app = falcon.App()
    app.req_options.auto_parse_form_urlencoded = True
    app.resp_options.secure_cookies_by_default = False
    app.add_static_route("/public", str(Path.cwd()/"todolists/public"))
    app.add_route("/", Index())
    app.add_route("/register", user_registration.UserRegistration())
    app.add_route("/email_verification", email_verification.EmailVerification())
    app.add_route("/login", user_authentication.UserAuthentication())
    app.add_route("/logout", user_authentication.UserLogout())
    app.add_route("/dashboard", user_dashboard.UserDashboard())
    app.add_route("/create-todolist", user_todolists.CreateTodolist())
    app.add_route("/get-todolist", user_todolists.ReadTodoList())
    app.add_route("/update-todolist", user_todolists.UpdateTodoList())
    app.add_route("/delete-todolist", user_todolists.DeleteTodoList())
    app.add_route("/create-task", user_tasks.CreateTask())
    app.add_route("/update-task", user_tasks.UpdateTask())
    app.add_route("/delete-task", user_tasks.DeleteTask())
    return app

app = create()
