import bcrypt
from secrets import token_hex

from falcon import testing
from psycopg2.errors import UniqueViolation

from todolists import app, db, redis_conn, user_dashboard


class TestUserDashboardCRUDFunctions(testing.TestCase):

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

    def test_function_create_todolist_on_db_returns_list_id(self):
        doc = user_dashboard.create_todolist(self.user_id, "todolist 1")
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT list_id, title FROM lists WHERE user_id = %s", [self.user_id])
                todolist = curs.fetchone()
        self.assertEqual(doc, todolist.list_id)
        self.assertEqual("todolist 1", todolist.title)

    def test_function_create_todolist_on_db_wont_accept_same_list_title(self):
        user_dashboard.create_todolist(self.user_id, "todolist 1")
        with self.assertRaises(UniqueViolation) as error:
            user_dashboard.create_todolist(self.user_id, "todolist 1")

    def test_function_get_todolist_list_id_by_user_id_and_list_title_from_db(self):
        doc = user_dashboard.create_todolist(self.user_id, "market")
        result = user_dashboard.get_todolist_list_id(self.user_id, "market")
        self.assertEqual(doc, result)

    def test_function_get_todolist_title_by_list_id(self):
        list_id = user_dashboard.create_todolist(self.user_id, "market")
        result = user_dashboard.get_todolist_title(list_id)
        self.assertEqual("market", result)

    def test_function_delete_todolist_from_db_by_list_id(self):
        list_id = user_dashboard.create_todolist(self.user_id, "my todolist")
        user_dashboard.delete_todolist(list_id)
        with self.assertRaises(ValueError) as error:
            user_dashboard.get_todolist_list_id(self.user_id, "my todolist")
        self.assertEqual(str(error.exception), "list_id not found.")

    def test_function_update_todolist_title_in_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "my todolist")
        user_dashboard.update_todolist_title(list_id, "my groceries")
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT title FROM lists where list_id = %s", [list_id])
                result = curs.fetchone().title
        self.assertNotEqual("my todolist", result)
        self.assertEqual("my groceries", result)

    def test_function_create_task_in_todolist_on_db_returns_task_id_incremented_correctly(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id_1 = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        task_id_2 = user_dashboard.create_task_in_todolist(list_id, "5 beers")
        self.assertEqual(task_id_1, task_id_2-1)

    def test_function_get_task_id_by_list_id_and_task_text_from_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        result = user_dashboard.get_task_id(list_id, "10 green apples")
        self.assertEqual(task_id, result)

    def test_function_delete_task_from_todolist_on_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.delete_task(task_id)
        with self.assertRaises(ValueError) as error:
            user_dashboard.get_task_id(list_id, "10 green apples")
        self.assertEqual(str(error.exception), "task_id not found.")

    def test_function_update_task_text_in_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.update_task_text(task_id, "5 beers")
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT task FROM tasks WHERE task_id = %s",[task_id])
                result = curs.fetchone().task
        self.assertNotEqual("10 green apples", result)
        self.assertEqual("5 beers", result)

    def test_function_mark_task_as_done_in_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.mark_task_as_done(task_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT done FROM tasks WHERE task_id = %s",[task_id])
                done = curs.fetchone().done
        self.assertTrue(done)

    def test_function_unmark_task_as_not_done_in_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.mark_task_as_done(task_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT done FROM tasks WHERE task_id = %s",[task_id])
                done = curs.fetchone().done
        self.assertTrue(done)
        user_dashboard.unmark_task_as_done(task_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT done FROM tasks WHERE task_id = %s",[task_id])
                done = curs.fetchone().done
        self.assertFalse(done)

    def test_function_get_tasks_of_selected_todolist_from_db(self):
        doc = {"10 green apples": False,
               "5 beers": False,
               "2 condoms": False}
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.create_task_in_todolist(list_id, "5 beers")
        user_dashboard.create_task_in_todolist(list_id, "2 condoms")
        result = user_dashboard.get_tasks_of_selected_todolist(list_id)
        self.assertEqual(doc, result)

    def test_fuction_get_empty_todolists_user_data(self):
        doc = {
            "author": "John Smith",
            "todolists": {},
            "selected_todolist": None
        }
        result = user_dashboard.get_todolists_user_data(self.user_id)
        self.assertEqual(doc, result)

    def test_fuction_get_todolists_user_data_with_todolists_but_no_tasks(self):
        doc = {
            "author": "John Smith",
            "todolists": {
                "Groceries": {},
                "Gym": {}
                },
            "selected_todolist": "Gym"
        }
        user_dashboard.create_todolist(self.user_id, "Groceries")
        user_dashboard.create_todolist(self.user_id, "Gym")
        result = user_dashboard.get_todolists_user_data(self.user_id, "Gym")
        self.assertEqual(doc, result)

    def test_function_get_todolists_user_data_with_todolists_and_tasks(self):
        doc = {
            "author": "John Smith",
            "todolists": {
                "Groceries": {},
                "Gym": {
                    "wrestling": True,
                    "football": False
                }
                },
            "selected_todolist": "Gym"
        }
        list_id = user_dashboard.create_todolist(self.user_id, "Groceries")
        user_dashboard.create_task_in_todolist(list_id, "5 carrots")
        list_id = user_dashboard.create_todolist(self.user_id, "Gym")
        task_id = user_dashboard.create_task_in_todolist(list_id, "wrestling")
        user_dashboard.mark_task_as_done(task_id)
        user_dashboard.create_task_in_todolist(list_id, "football")
        result = user_dashboard.get_todolists_user_data(self.user_id, "Gym")
        self.assertEqual(doc, result)

    def test_function_get_todolists_user_data_selects_first_list_if_none_is_passed_as_arg(self):
        doc = {
            "author": "John Smith",
            "todolists": {
                "Market": {},
                "Gym": {}
            },
            "selected_todolist": "Market"
        }
        user_dashboard.create_todolist(self.user_id, "Market")
        user_dashboard.create_todolist(self.user_id, "Gym")
        result = user_dashboard.get_todolists_user_data(self.user_id)
        self.assertEqual(doc, result)


class TestUserDashboardInterfaceHandlesTodolists(testing.TestCase):

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

    def test_user_dashboard_renders_no_lists_page_on_get(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {},
            "selected_todolist": None
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_lists_created_todolists_if_any(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "todolist 3": {},
                "todolist 4": {}
            },
            "selected_todolist": "todolist 3"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        user_dashboard.create_todolist(self.user_id, "todolist 3")
        user_dashboard.create_todolist(self.user_id, "todolist 4")
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_renders_selected_unique_created_todolist_page_on_get(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "my todolist": {},
            },
            "selected_todolist": "my todolist"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        user_dashboard.create_todolist(self.user_id, "my todolist")
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token},)
        self.assertEqual(doc, result.text)

    def test_user_dashboard_creates_todolist_when_create_todolist_button_clicked(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "my todolist": {},
            },
            "selected_todolist": "my todolist"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token}, 
                                     params={"todolist-create": "my todolist"})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_selects_just_created_todolist(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "my todolist": {},
                "groceries": {}
            },
            "selected_todolist": "groceries"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        user_dashboard.create_todolist(self.user_id, "my todolist")
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token},
                                    params={"todolist-create": "groceries"})
        self.maxDiff = None
        self.assertEqual(doc, result.text)

    def test_user_dashboard_loads_todolist_selected_by_user(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "my todolist": {},
                "groceries": {}
            },
            "selected_todolist": "my todolist"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        user_dashboard.create_todolist(self.user_id, "my todolist")
        user_dashboard.create_todolist(self.user_id, "groceries")
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token},
                                    params={"todolist-load": "my todolist"})
        print(result.text)
        self.assertEqual(doc, result.text)

    def test_user_dashboard_deletes_selected_todolist(self):
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                "my todolist": {},
            },
            "selected_todolist": "my todolist"
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        user_dashboard.create_todolist(self.user_id, "my todolist")
        user_dashboard.create_todolist(self.user_id, "groceries")
        result = self.simulate_post("/dashboard", cookies={"session-token": self.session_token},
                                    params={"todolist-delete": "groceries"})
        self.assertEqual(doc, result.text)


class TestUserDashboardInterfaceHandlesTasks(testing.TestCase):

    @classmethod
    def setUpClass(cls):
        add_verified_user()
        cls.user_id = get_user_id("john12@fake.com")
        cls.session_token = create_session_token()
        set_session_token_on_redis(cls.session_token, cls.user_id)
        cls.gym_list_id = user_dashboard.create_todolist(cls.user_id, "Gym")
        cls.market_list_id = user_dashboard.create_todolist(cls.user_id, "Market")
        cls.work_list_id = user_dashboard.create_todolist(cls.user_id, "Work")

    @classmethod
    def tearDownClass(cls):
        flushall_from_redis()
        truncate_tasks()
        truncate_users()


    def setUp(self):
        super().setUp()
        self.app = app.create()
        truncate_tasks()

    def test_user_dashboard_displays_tasks_of_selected_todolist(self):
        user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        user_dashboard.create_task_in_todolist(self.gym_list_id, "Swimming")
        todolists_user = user_dashboard.get_todolists_user_data(self.user_id, "Gym")
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        self.assertTrue("Running" in doc)
        self.assertTrue("Swimming" in doc)


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
            curs.execute("TRUNCATE lists CASCADE;") 

def truncate_users():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE users CASCADE;")

def truncate_tasks():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE tasks CASCADE;")

def flushall_from_redis():
    with redis_conn.conn as conn:
        conn.flushall()
