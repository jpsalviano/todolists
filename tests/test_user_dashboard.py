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
        doc = app.templates_env.get_template("dashboard.html")
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc.render(user_id=self.user_id), result.text)

    def test_create_todolist_on_db(self):
        user_dashboard.create_todolist_on_db("todolist 1", self.user_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT title FROM lists WHERE user_id = %s", [self.user_id])
                self.assertEqual("todolist 1", curs.fetchone().title)
        truncate_lists()

    def test_create_user_todolists_dict(self):
        user_dashboard.create_todolist_on_db("todolist 1", self.user_id)
        user_dashboard.create_todolist_on_db("todolist 2", self.user_id)
        user_todolists_dict = {
            "user_name": "John Smith",
            "todolists": {
                "todolist 1": {},
                "todolist 2": {}
            }
        }
        result = user_dashboard.create_user_todolists_dict(self.user_id)
        truncate_lists()

    def test_user_dashboard_loads_created_lists_if_any(self):
        user_dashboard.create_todolist_on_db("todolist 3", self.user_id)
        user_dashboard.create_todolist_on_db("todolist 4", self.user_id)
        doc = app.templates_env.get_template("dashboard.html")
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc.render(user_id=self.user_id), result.text)
        truncate_lists()


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
