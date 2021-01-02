import falcon

from todolists import app, db


class UserTodoLists:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        template = app.templates_env.get_template("dashboard.html")
        resp.text = template.render(user_id="", todo_lists=[])