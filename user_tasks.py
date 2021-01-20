import falcon

from todolists import app, db, redis_conn
from todolists.user_dashboard import get_todolists_user_data
from todolists.user_authorization import check_session_token, AuthorizationError


class CreateTask:
    def on_post(self, req, resp):
        resp.content_type="text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
        except AuthorizationError as error:
            resp.status = falcon.HTTP_401
            template = app.templates_env.get_template("error.html")
            resp.text = template.render(error=error)
        except:
            resp.status = falcon.HTTP_500
            resp.text = template.render(error="Contact the website owner.")
        else:
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
        selected_todolist = req.get_param("selected-todolist")
        task_id = req.get_param("update-task")
        done = req.get_param("mark-task")
        if done == "false":
            done = False
        else:
            done = True
        mark_task(int(task_id), done)
        template = app.templates_env.get_template("dashboard.html")
        user_data = get_todolists_user_data(user_id, int(selected_todolist))
        resp.text = template.render(user=user_data)


class DeleteTask:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
        user_id = check_session_token(req.cookies["session-token"])
        selected_todolist, task_id = req.get_param("selected-todolist"), req.get_param("delete-task")
        delete_task(int(task_id))
        template = app.templates_env.get_template("dashboard.html")
        user_data = get_todolists_user_data(user_id, int(selected_todolist))
        resp.text = template.render(user=user_data)


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
            if done:
                curs.execute("UPDATE tasks SET done = true WHERE task_id = %s", [task_id])
            else:
                curs.execute("UPDATE tasks SET done = false WHERE task_id = %s", [task_id])
