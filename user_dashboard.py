import falcon

from todolists import app, db, redis_conn


class UserTodoLists:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("dashboard.html")
            todolists_user = get_todolists_user_data(user_id)
            resp.text = template.render(user=todolists_user)
        except:
            resp.status = falcon.HTTP_401
            resp.text = falcon.HTTP_401

    def on_post(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
        except:
            resp.status = falcon.HTTP_401
            resp.text = falcon.HTTP_401
        else:
            if req.get_param("todolist-create"):
                create_todolist(user_id, req.get_param("todolist-create"))
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user_data(user_id,
                                            selected_todolist=req.get_param("todolist-create")))
            elif req.get_param("todolist-load"):
                selected_todolist = req.get_param("todolist-load")
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user_data(user_id, selected_todolist))
            elif req.get_param("todolist-delete"):
                list_id = get_todolist_list_id(user_id, req.get_param("todolist-delete"))
                delete_todolist(list_id)
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user_data(user_id))
            elif req.get_param("add-task"):
                selected_todolist = req.get_param("selected_todolist")
                task = req.get_param("add-task")
                list_id = get_todolist_list_id(user_id, selected_todolist)
                task_id = create_task_in_todolist(list_id, task)
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user_data(user_id, selected_todolist))


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

def create_todolist(user_id, title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO lists (title, user_id) VALUES (%s, %s) RETURNING list_id", [title, user_id])
            try:
                return curs.fetchone().list_id
            except:
                raise ValueError("You cannot create another TodoList with this title.")

def get_todolist_list_id(user_id, list_title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT list_id FROM lists WHERE user_id = %s AND title = %s", [user_id, list_title])
            try:
                return curs.fetchone().list_id
            except:
                raise ValueError("list_id not found.")

def get_todolist_title(list_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT title FROM lists WHERE list_id = %s", [list_id])
            return curs.fetchone().title

def delete_todolist(list_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM lists WHERE list_id = %s;DELETE FROM tasks WHERE list_id IN (SELECT list_id FROM tasks); DELETE FROM tasks;", [list_id])

def update_todolist_title(list_id, new_title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE lists SET title = %s WHERE list_id = %s", [new_title, list_id])

def create_task_in_todolist(list_id, task):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO tasks (task, list_id) VALUES (%s, %s) RETURNING task_id", [task, list_id])
            return curs.fetchone().task_id

def get_task_id(list_id, task):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT task_id FROM tasks WHERE list_id = %s AND task = %s", [list_id, task])
            try:
                return curs.fetchone().task_id
            except:
                raise ValueError("task_id not found.")

def delete_task(task_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM tasks WHERE task_id = %s", [task_id])

def update_task_text(task_id, new_text):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE tasks SET task = %s WHERE task_id = %s", [new_text, task_id])

def mark_task_as_done(task_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE tasks SET done = true WHERE task_id = %s", [task_id])

def unmark_task_as_done(task_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE tasks SET done = false WHERE task_id = %s", [task_id])

def get_tasks_of_selected_todolist(list_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT task, done FROM tasks WHERE list_id = %s", [list_id])
            records = curs.fetchall()
    tasks = {}
    for r in records:
        tasks[r.task] = r.done
    return tasks

def get_todolists_user_data(user_id, selected_todolist=None):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT name FROM users WHERE user_id = %s", [user_id])
            author = curs.fetchone().name
            curs.execute("SELECT title, list_id FROM lists WHERE user_id = %s", [user_id])
            todolists = curs.fetchall()
    todolists_user = {
        "author": author,
        "todolists": {},
        "selected_todolist": selected_todolist
    }
    if todolists:
        list_ids = []
        for todolist in todolists:
            list_ids.append(int(todolist.list_id))
            todolists_user["todolists"][todolist.title] = {}
        if selected_todolist==None:
            list_id = min(list_ids)
            selected_todolist = get_todolist_title(list_id)
            tasks = get_tasks_of_selected_todolist(list_id)
            todolists_user["todolists"][selected_todolist] = tasks
            todolists_user["selected_todolist"] = selected_todolist
        else:
            list_id = get_todolist_list_id(user_id, selected_todolist)
            tasks = get_tasks_of_selected_todolist(list_id)
            todolists_user["todolists"][selected_todolist] = tasks
    return todolists_user