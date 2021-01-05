import bcrypt
from secrets import token_hex

from falcon import testing

from todolists import app, db, redis_conn, user_dashboard


class TestUserTodoListsLoggedUser(testing.TestCase):

    @classmethod
    def setUpClass(cls):
        add_verified_user()
        cls.user_id = get_user_id("john12@fake.com")
        cls.session_token = create_session_token()
        set_session_token_on_redis(cls.session_token, cls.user_id)

    @classmethod
    def tearDownClass(cls):
        flushall_from_redis()
        truncate_users()

    def setUp(self):
        super().setUp()
        self.app = app.create()

    def test_user_dashboard_loads_no_lists_page(self):
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_dashboard.create_user_todolists_dict(self.user_id))
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_create_todolist_on_db(self):
        truncate_lists()
        user_dashboard.create_todolist_on_db("todolist 1", self.user_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT title FROM lists WHERE user_id = %s", [self.user_id])
                self.assertEqual("todolist 1", curs.fetchone().title)

    def test_create_user_todolists_dict(self):
        truncate_lists()
        user_dashboard.create_todolist_on_db("todolist 1", self.user_id)
        user_dashboard.create_todolist_on_db("todolist 2", self.user_id)
        user_todolists_dict = {
            "name": "John Smith",
            "todolists": {
                "todolist 1": {"tasks": {}},
                "todolist 2": {"tasks": {}}
            },
            "selected": ""
        }
        result = user_dashboard.create_user_todolists_dict(self.user_id)
        self.assertEqual(user_todolists_dict, result)

    def test_user_dashboard_loads_created_lists_if_any(self):
        truncate_lists()
        user_todolists_dict = {
            "name": "John Smith",
            "todolists": {
                "todolist 3": {"tasks": {}},
                "todolist 4": {"tasks": {}}
            },
            "selected": ""
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_todolists_dict)
        user_dashboard.create_todolist_on_db("todolist 3", self.user_id)
        user_dashboard.create_todolist_on_db("todolist 4", self.user_id)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_creates_todolist_on_create_todolist_button(self):
        truncate_lists()
        user_todolists_dict = {
            "name": "John Smith",
            "todolists": {
                "my todolist": {"tasks": {}},
            },
            "selected": "my todolist"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_todolists_dict)
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token}, 
                                     params={"todolist-create": "my todolist"})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_displays_todolist_if_selected(self):
        truncate_lists()
        user_todolists_dict = {
            "name": "John Smith",
            "todolists": {
                "my todolist": {"tasks": {}},
                "groceries": {"tasks": {}}
            },
            "selected": "groceries"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_todolists_dict)
        user_dashboard.create_todolist_on_db("my todolist", self.user_id)
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token},
                                    params={"todolist-create": "groceries"})
        self.assertEqual(doc, result.text)


def add_verified_user():
    hashed = bcrypt.hashpw("123abc-".encode(), bcrypt.gensalt())
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO users (name, email, password) \
               VALUES ('John Smith', 'john12@fake.com', %s)", [hashed.decode()])
            curs.execute("UPDATE users SET verified=true WHERE email='john12@fake.com'")

def get_user_id(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT user_id FROM users WHERE email = %s", [email])
            return str(curs.fetchone().user_id)

def create_session_token():
    return token_hex(32)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.conn as conn:
        conn.set(session_token, user_id)

def truncate_lists():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE lists;") 

def truncate_users():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE users CASCADE;")

def flushall_from_redis():
    with redis_conn.conn as conn:
        conn.flushall()
