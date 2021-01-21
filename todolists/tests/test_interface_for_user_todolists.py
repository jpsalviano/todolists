import bcrypt
from secrets import token_hex

from falcon import testing

from todolists import app, db, redis_conn, user_dashboard, user_todolists


class TestUserInteractionWithTodolists(testing.TestCase):

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
        truncate_lists()

    def test_interface_renders_no_user_todolists_page(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {},
            "selected_todolist": None
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_interface_renders_list_of_created_todolists_if_any(self):
        list_id_3 = user_todolists.create_todolist(self.user_id, "todolist 3")
        list_id_4 = user_todolists.create_todolist(self.user_id, "todolist 4")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                list_id_3: {
                    "title": "todolist 3",
                    "tasks": {}
                },
                list_id_4: {
                    "title": "todolist 4",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id_3
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_interface_renders_selected_single_created_todolist_page(self):
        list_id = user_todolists.create_todolist(self.user_id, "my todolist")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                list_id: {
                    "title": "my todolist",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token},)
        self.assertEqual(doc, result.text)

    def test_interface_renders_page_including_created_todolist_when_create_todolist_button_clicked(self):
        result = self.simulate_post("/create-todolist", cookies={"session-token": self.session_token}, 
                                    params={"create-todolist": "my todolist"})
        list_id = get_todolist_id(self.user_id, "my todolist")
        user_data = {
            "author": "John Smith",
            "todolists": {
                list_id: {
                    "title": "my todolist",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        self.assertEqual(doc, result.text)

    def test_interface_renders_page_with_just_created_todolist_selected(self):
        list_id_1 = user_todolists.create_todolist(self.user_id, "my todolist")
        result = self.simulate_post("/create-todolist", cookies={"session-token": self.session_token},
                                    params={"create-todolist": "groceries"})
        list_id_2 = get_todolist_id(self.user_id, "groceries")
        user_data = user_dashboard.get_todolists_user_data(self.user_id, list_id_2)
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        self.assertEqual(doc, result.text)

    def test_interface_loads_todolist_selected_by_user(self):
        list_id_1 = user_todolists.create_todolist(self.user_id, "my todolist")
        list_id_2 = user_todolists.create_todolist(self.user_id, "groceries")
        list_id_3 = user_todolists.create_todolist(self.user_id, "gym")
        user_data = user_dashboard.get_todolists_user_data(self.user_id, list_id_2)
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_post("/get-todolist", cookies={"session-token": self.session_token},
                                    params={"get-todolist": list_id_2})
        self.assertEqual(doc, result.text)

    def test_interface_gets_updated_selected_todolist_title(self):
        list_id = user_todolists.create_todolist(self.user_id, "Market")
        doc_user_data = {
            "author": "John Smith",
            "todolists": {
                list_id: {
                    "title": "Supermarket",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=doc_user_data)
        result = self.simulate_post("/update-todolist", cookies={"session-token": self.session_token},
                                    params={"update-todolist": list_id, "change-todolist-title": "Supermarket"})
        self.assertEqual(doc, result.text)

    def test_interface_loads_page_without_selected_todolist_after_delete_button_clicked(self):
        list_id_1 = user_todolists.create_todolist(self.user_id, "my todolist")
        list_id_2 = user_todolists.create_todolist(self.user_id, "groceries")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "my todolist",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id_1
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_post("/delete-todolist", cookies={"session-token": self.session_token},
                                    params={"delete-todolist": list_id_2})
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
            return curs.fetchone().user_id

def get_todolist_id(user_id, title):
    print(user_id, title)
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("SELECT list_id FROM lists WHERE user_id = %s AND title = %s", [user_id, title])
            return curs.fetchone().list_id

def create_session_token():
    return token_hex(32)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.session_conn as conn:
        conn.set(session_token, user_id)

def truncate_lists():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE lists CASCADE;") 

def truncate_users():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE users CASCADE;")

def flushall_from_redis():
    with redis_conn.session_conn as conn:
        conn.flushall()
