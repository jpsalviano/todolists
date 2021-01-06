import falcon

from todolists import app, db, redis_conn


class UserTodoLists:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("dashboard.html")
            todolists_user = get_todolists_user(user_id)
            if todolists_user["todolists"] != {} and todolists_user["selected"] == "":
                todolists_user["selected"] = list(todolists_user["todolists"])[0]
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
                create_todolist_on_db(req.get_param("todolist-create"), user_id)
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user(user_id,
                                            selected=req.get_param("todolist-create")))
            elif req.get_param("todolist-load"):
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user(user_id,
                                            selected=req.get_param("todolist-load")))
            elif req.get_param("todolist-delete"):
                delete_todolist_from_db(req.get_param("todolist-delete"), user_id)
                template = app.templates_env.get_template("dashboard.html")
                resp.text = template.render(user=get_todolists_user(user_id))


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


def create_todolist_on_db(title, user_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO lists (title, user_id) VALUES (%s, %s)", [title, user_id])

def get_todolists_user(user_id, selected=""):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT name FROM users WHERE user_id = %s", [user_id])
            name = curs.fetchone().name
            curs.execute("SELECT title FROM lists WHERE user_id = %s", [user_id])
            todolists = curs.fetchall()
    todolists_user = {
        "author": name,
        "todolists": {},
        "selected": selected
    }
    for todolist in todolists:
        todolists_user["todolists"][todolist.title] = {"tasks":{}}
    return todolists_user

def check_session_token(session_token):
    with redis_conn.conn as conn:
        user_id = conn.get(session_token)
        if user_id:
            return user_id.decode()
        else:
            raise AuthenticationError("Unauthorized.")

def delete_todolist_from_db(todolist, user_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM lists WHERE user_id = %s AND title = %s", [user_id, todolist])