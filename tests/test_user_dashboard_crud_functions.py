import bcrypt
from secrets import token_hex

from falcon import testing
from psycopg2.errors import UniqueViolation, ProgrammingError

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
        truncate_tasks()

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

    def test_function_delete_todolist_from_db_by_list_id(self):
        list_id = user_dashboard.create_todolist(self.user_id, "my todolist")
        user_dashboard.delete_todolist(list_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT title FROM lists WHERE list_id = %s", [list_id])
                with self.assertRaises(AttributeError) as error:
                    curs.fetchone().list_id
        self.assertEqual(str(error.exception), "'NoneType' object has no attribute 'list_id'")

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

    def test_function_delete_task_from_todolist_on_db(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        user_dashboard.delete_task(task_id)
        self.assertTrue(task_id)
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT task FROM tasks WHERE task_id = %s", [task_id])
                with self.assertRaises(AttributeError) as error:
                    curs.fetchone().task
        self.assertEqual(str(error.exception), "'NoneType' object has no attribute 'task'")

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
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
        task_id_1 = user_dashboard.create_task_in_todolist(list_id, "10 green apples")
        task_id_2 = user_dashboard.create_task_in_todolist(list_id, "5 beers")
        task_id_3 = user_dashboard.create_task_in_todolist(list_id, "2 condoms")
        doc = {
            task_id_1: {
                "task": "10 green apples",
                "done": False
            },
            task_id_2: {
                "task": "5 beers",
                "done": False
            },
            task_id_3: {
                "task": "2 condoms",
                "done": False}
            }
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
        list_id_1 = user_dashboard.create_todolist(self.user_id, "Groceries")
        list_id_2 = user_dashboard.create_todolist(self.user_id, "Gym")
        doc = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "Groceries",
                    "tasks": {}
                },
                list_id_2: {
                    "title": "Gym",
                    "tasks": {}
                }},
            "selected_todolist": list_id_2
        }
        result = user_dashboard.get_todolists_user_data(self.user_id, list_id_2)
        self.assertEqual(doc, result)

    def test_function_get_todolists_user_data_with_todolists_and_tasks(self):
        list_id_1 = user_dashboard.create_todolist(self.user_id, "Groceries")
        task_id_1 = user_dashboard.create_task_in_todolist(list_id_1, "beers")
        list_id_2 = user_dashboard.create_todolist(self.user_id, "Gym")
        task_id_2 = user_dashboard.create_task_in_todolist(list_id_2, "wrestling")
        user_dashboard.mark_task_as_done(task_id_2)
        task_id_3 = user_dashboard.create_task_in_todolist(list_id_2, "football")
        doc = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "Groceries",
                    "tasks": {}
                    },
                list_id_2: {
                    "title": "Gym",
                    "tasks": {
                        task_id_2: {
                            "task": "wrestling",
                            "done": True},
                        task_id_3: {
                            "task": "football",
                            "done": False}
                        }}},
            "selected_todolist": list_id_2
            }
        result = user_dashboard.get_todolists_user_data(self.user_id, list_id_2)
        self.maxDiff = None
        self.assertEqual(doc, result)

    def test_function_get_todolists_user_data_selects_first_list_if_none_is_passed_as_arg(self):
        list_id_1 = user_dashboard.create_todolist(self.user_id, "Market")
        list_id_2 = user_dashboard.create_todolist(self.user_id, "Gym")
        doc = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "Market",
                    "tasks": {}
                },
                list_id_2: {
                    "title": "Gym",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id_1
        }
        result = user_dashboard.get_todolists_user_data(self.user_id)
        self.assertEqual(doc, result)


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
