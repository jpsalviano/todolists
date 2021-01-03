import falcon

from todolists import app, db, redis_conn


class UserTodoLists:
    def on_get(self, req, resp):
        resp.content_type = "text/html"
        try:
            user_id = check_session_token(req.cookies["session-token"])
            template = app.templates_env.get_template("dashboard.html")
            resp.text = template.render(user_id=user_id)
        except:
            resp.status = falcon.HTTP_401
            resp.text = falcon.HTTP_401


class AuthenticationError(Exception):
    def __init__(self, message):
        self.message = message


def create_todolist_on_db(title, user_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO lists (title, user_id) VALUES (%s, %s)", [title, user_id])

def create_user_todolists_dict(user_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT name FROM users WHERE user_id = %s", [user_id])
            name = curs.fetchone().name
            curs.execute("SELECT title FROM lists WHERE user_id = %s", [user_id])
            todolists = curs.fetchall()
    user_todolists_dict = {
        "user_name": name,
        "todolists": {}
    }
    for todolist in todolists:
        user_todolists_dict["todolists"][todolist] = {}
    return user_todolists_dict

def check_session_token(session_token):
    with redis_conn.conn as conn:
        user_id = conn.get(session_token)
        if user_id:
            return user_id.decode()
        else:
            raise AuthenticationError("Unauthorized.")