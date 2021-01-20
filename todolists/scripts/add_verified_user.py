import bcrypt
from todolists import db

def add_verified_user_with_list_and_tasks():
    hashed = bcrypt.hashpw("1".encode(), bcrypt.gensalt())
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO users (name, email, password) \
               VALUES ('John Smith', 'john12@fake.com', %s) RETURNING user_id", [hashed.decode()])
            user_id = curs.fetchone().user_id
            curs.execute("UPDATE users SET verified=true WHERE user_id=%s", [user_id])
            curs.execute("INSERT INTO lists (title, user_id) VALUES ('Gym', %s) RETURNING list_id", [user_id])
            list_id = curs.fetchone().list_id
            curs.execute("INSERT INTO tasks (task, list_id) VALUES ('Running', %s)", [list_id])
            curs.execute("INSERT INTO tasks (task, list_id) VALUES ('Swimming', %s)", [list_id])

add_verified_user_with_list_and_tasks()