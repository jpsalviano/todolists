import bcrypt
from secrets import token_hex

from falcon import testing

from todolists import app, db, redis_conn, user_tasks



class TestUserInteractionWithTasks(testing.TestCase):

    @classmethod
    def setUpClass(cls):
        add_verified_user()
        cls.user_id = get_user_id("john12@fake.com")
        cls.session_token = create_session_token()
        set_session_token_on_redis(cls.session_token, cls.user_id)
        cls.gym_list_id = create_todolist(cls.user_id, "Gym")
        cls.market_list_id = create_todolist(cls.user_id, "Market")
        cls.work_list_id = create_todolist(cls.user_id, "Work")

    @classmethod
    def tearDownClass(cls):
        flushall_from_redis()
        truncate_tasks()
        truncate_users()

    def setUp(self):
        super().setUp()
        self.app = app.create()
        truncate_tasks()

    def test_interface_displays_tasks_of_oldest_created_todolist_if_any(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        task_id_gym_2 = user_tasks.create_task_in_todolist(self.gym_list_id, "Swimming")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_id_gym_2: {
                            "task": "Swimming",
                            "done": False
                        }
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_interface_displays_tasks_of_selected_and_loaded_todolist(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        task_id_gym_2 = user_tasks.create_task_in_todolist(self.gym_list_id, "Swimming")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_id_gym_2: {
                            "task": "Swimming",
                            "done": False
                        }
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_post("/get-todolist", cookies={"session-token": self.session_token},
                                    params={"get-todolist": self.gym_list_id})
        self.maxDiff = None
        self.assertEqual(doc, result.text)

    def test_interface_renders_page_with_created_task_on_selected_todolist_when_add_task_button_is_clicked_with_valid_input(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        truncate_tasks()
        result = self.simulate_post("/create-task", cookies={"session-token": self.session_token},
                                    params={"selected-todolist": self.gym_list_id, "create-task": "Running"})
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT task_id FROM tasks WHERE list_id = %s AND task = 'Running'", [self.gym_list_id])
                new_task_id_gym_1 = curs.fetchone().task_id
        self.assertTrue(task_id_gym_1 == new_task_id_gym_1-1)

    def test_interface_displays_task_as_done_when_done_button_is_pressed(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        task_id_gym_2 = user_tasks.create_task_in_todolist(self.gym_list_id, "Swimming")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_id_gym_2: {
                            "task": "Swimming",
                            "done": True
                        }
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_post("/update-task", cookies={"session-token": self.session_token},
                           params={"selected-todolist": self.gym_list_id, "update-task": task_id_gym_2, 
                                   "mark-task": "true"})
        self.assertEqual(doc, result.text)

    def test_interface_displays_task_as_undone_when_undone_button_is_pressed(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        user_tasks.mark_task(task_id_gym_1, "true")
        task_id_gym_2 = user_tasks.create_task_in_todolist(self.gym_list_id, "Swimming")
        user_tasks.mark_task(task_id_gym_2, "true")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": True
                        },
                        task_id_gym_2: {
                            "task": "Swimming",
                            "done": False
                        }
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_post("/update-task", cookies={"session-token": self.session_token},
                                    params={"selected-todolist": self.gym_list_id, "update-task": task_id_gym_2,
                                            "mark-task": "false"})
        self.assertEqual(doc, result.text)

    def test_interface_no_longer_shows_task_when_delete_button_is_clicked(self):
        task_id_gym_1 = user_tasks.create_task_in_todolist(self.gym_list_id, "Running")
        task_id_gym_2 = user_tasks.create_task_in_todolist(self.gym_list_id, "Swimming")
        task_id_gym_3 = user_tasks.create_task_in_todolist(self.gym_list_id, "Football")
        user_data = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_id_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_id_gym_2: {
                            "task": "Swimming",
                            "done": False
                        }
                    }
                },
                self.market_list_id: {
                    "title": "Market",
                    "tasks": {}
                },
                self.work_list_id: {
                    "title": "Work",
                    "tasks": {}
                }
            },
            "selected_todolist": self.gym_list_id
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=user_data)
        result = self.simulate_post("/delete-task", cookies={"session-token": self.session_token},
                                    params={"selected-todolist": self.gym_list_id, "delete-task": task_id_gym_3})
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

def create_session_token():
    return token_hex(32)

def set_session_token_on_redis(session_token, user_id):
    with redis_conn.conn as conn:
        conn.set(session_token, user_id)

def create_todolist(user_id, title):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("INSERT INTO lists (title, user_id) VALUES (%s, %s) RETURNING list_id", [title, user_id])
            try:
                return curs.fetchone().list_id
            except:
                raise ValueError("You cannot create another TodoList with this title.")

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