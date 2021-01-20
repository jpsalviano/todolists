import falcon

from todolists import app, db, redis_conn
from todolists.user_dashboard import get_todolists_user_data


class CreateTask:
    def on_post(self, req, resp):
        resp.content_type="text/html"
        user_id = check_session_token(req.cookies["session-token"])
        selected_todolist = int(req.get_param("selected-todolist"))
        new_task = req.get_param("create-task")
        create_task_in_todolist(selected_todolist, new_task)
        template = app.templates_env.get_template("dashboard.html")
        user_data = get_todolists_user_data(user_id, selected_todolist)
        resp.text = template.render(user=user_data)


class UpdateTask:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        user_id = check_session_token(req.cookies["session-token"])
        selected_todolist, task_id, done = req.get_param("update-task").split(";")
        mark_task(int(task_id), done)
        template = app.templates_env.get_template("dashboard.html")
        user_data = get_todolists_user_data(user_id, int(selected_todolist))
        resp.text = template.render(user=user_data)


class DeleteTask:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        user_id = check_session_token(req.cookies["session-token"])
        selected_todolist, task_id = req.get_param("delete-task").split(";")
        delete_task(int(task_id))
        template = app.templates_env.get_template("dashboard.html")
        user_data = get_todolists_user_data(user_id, int(selected_todolist))
        resp.text = template.render(user=user_data)


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


def check_session_token(session_token):
    with redis_conn.conn as conn:
        user_id = conn.get(session_token)
        if user_id:
            return user_id.decode()
        else:
            raise AuthenticationError("Unauthorized.")

def create_task_in_todolist(list_id, task):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO tasks (list_id, task) VALUES (%s, %s) RETURNING task_id", [list_id, task])
            return curs.fetchone().task_id

def delete_task(task_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM tasks WHERE task_id = %s", [task_id])

def update_task_text(task_id, new_text):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE tasks SET task = %s WHERE task_id = %s", [new_text, task_id])

def mark_task(task_id, done):
    with db.conn as conn:
        with conn.cursor() as curs:
            if done=="true":
                curs.execute("UPDATE tasks SET done = true WHERE task_id = %s", [task_id])
            elif done=="false":
                curs.execute("UPDATE tasks SET done = false WHERE task_id = %s", [task_id])
