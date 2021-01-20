import falcon

from todolists import app, db, redis_conn
from todolists.user_dashboard import get_todolists_user_data
from todolists.user_authorization import check_session_token, AuthorizationError


class CreateTodolist:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
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
            list_id = create_todolist(user_id, req.get_param("create-todolist"))
            template = app.templates_env.get_template("dashboard.html")
            user_data = get_todolists_user_data(user_id, selected_todolist=list_id)
            resp.text = template.render(user=user_data)


class ReadTodoList:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
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
            selected_todolist = int(req.get_param("get-todolist"))
            template = app.templates_env.get_template("dashboard.html")
            user_data = get_todolists_user_data(user_id, selected_todolist)
            resp.text = template.render(user=user_data)


class UpdateTodoList:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
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
            selected_todolist = int(req.get_param("update-todolist"))
            new_title = req.get_param("change-todolist-title")
            update_todolist_title(selected_todolist, new_title)
            template = app.templates_env.get_template("dashboard.html")
            user_data = get_todolists_user_data(user_id, selected_todolist)
            resp.text = template.render(user=user_data)


class DeleteTodoList:
    def on_post(self, req, resp):
        resp.content_type = "text/html"
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
            selected_todolist = int(req.get_param("delete-todolist"))
            delete_todolist(selected_todolist)
            template = app.templates_env.get_template("dashboard.html")
            user_data = get_todolists_user_data(user_id)
            resp.text = template.render(user=user_data)


def create_todolist(user_id, title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO lists (title, user_id) VALUES (%s, %s) RETURNING list_id", [title, user_id])
            try:
                return curs.fetchone().list_id
            except:
                raise ValueError("You cannot create another TodoList with this title.")

def update_todolist_title(list_id, new_title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("UPDATE lists SET title = %s WHERE list_id = %s", [new_title, list_id])

def delete_todolist(list_id):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("DELETE FROM tasks WHERE list_id IN (SELECT %s FROM tasks); DELETE FROM lists WHERE list_id = %s;", [list_id, list_id])