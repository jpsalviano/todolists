import falcon

from todolists import app, db, redis_conn


class UserDashboard:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("dashboard.html")
            user_data = get_todolists_user_data(user_id)
            resp.text = template.render(user=user_data)
        except:
            resp.status = falcon.HTTP_401
            template = app.templates_env.get_template("login.html")


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

def get_todolists_user_data(user_id, selected_todolist=None):
    author, todolists = get_user_name_and_todolists(user_id)
    todolists_user_data = generate_user_data_dict(author, selected_todolist, todolists)
    if selected_todolist==None and todolists:
        select_oldest_todolist_if_any(todolists_user_data)
        selected_todolist = todolists_user_data["selected_todolist"]
    if selected_todolist:
        tasks = get_tasks_of_selected_todolist(selected_todolist)
        todolists_user_data["todolists"][selected_todolist]["tasks"] = tasks
    return todolists_user_data

def get_user_name_and_todolists(user_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT name FROM users WHERE user_id = %s", [user_id])
            author = curs.fetchone().name
            curs.execute("SELECT title, list_id FROM lists WHERE user_id = %s", [user_id])
            todolists = curs.fetchall()
    return (author, todolists)

def generate_user_data_dict(author, selected_todolist, todolists=None):
    todolists_user_data = {
        "author": author,
        "todolists": {},
        "selected_todolist": selected_todolist
    }
    if todolists:
        for todolist in todolists:
            todolists_user_data["todolists"][todolist.list_id] = {"title": todolist.title,
                                                                  "tasks": {}}
    return todolists_user_data

def select_oldest_todolist_if_any(todolists_user_data):
    selected_todolist = min(todolists_user_data["todolists"].keys())
    todolists_user_data["selected_todolist"] = selected_todolist
    return todolists_user_data

def get_tasks_of_selected_todolist(list_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT task_id, task, done FROM tasks WHERE list_id = %s", [list_id])
            records = curs.fetchall()
    tasks = {}
    for r in records:
        tasks[r.task_id] = {"task": r.task, "done": r.done}
    return tasks
