import bcrypt
from secrets import token_hex

from falcon import testing

from todolists import app, db, redis_conn, user_dashboard



class TestUserDashboardManagesTodolists(testing.TestCase):

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

    def test_user_dashboard_renders_no_user_todolists_page(self):
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
        list_id_3 = user_dashboard.create_todolist(self.user_id, "todolist 3")
        list_id_4 = user_dashboard.create_todolist(self.user_id, "todolist 4")
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

    def test_user_dashboard_renders_selected_single_created_todolist_page(self):
        list_id = user_dashboard.create_todolist(self.user_id, "my todolist")
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

    def test_user_dashboard_creates_todolist_when_create_todolist_button_clicked(self):
        result = self.simulate_post("/create-todolist", cookies={"session-token": self.session_token}, 
                                     params={"create-todolist": "my todolist"})
        self.assertTrue("my todolist" in result.text)

    def test_user_dashboard_selects_just_created_todolist(self):
        list_id_1 = user_dashboard.create_todolist(self.user_id, "my todolist")
        result = self.simulate_post("/create-todolist", cookies={"session-token": self.session_token},
                                    params={"create-todolist": "groceries"})
        list_id_2 = get_todolist_id(self.user_id, "groceries")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "my todolist",
                    "tasks": {}
                },
                list_id_2: {
                    "title": "groceries",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id_2
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        self.assertEqual(doc, result.text)

    def test_user_dashboard_loads_todolist_selected_by_user(self):
        list_id_1 = user_dashboard.create_todolist(self.user_id, "my todolist")
        list_id_2 = user_dashboard.create_todolist(self.user_id, "groceries")
        list_id_3 = user_dashboard.create_todolist(self.user_id, "gym")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                list_id_1: {
                    "title": "my todolist",
                    "tasks": {}
                },
                list_id_2: {
                    "title": "groceries",
                    "tasks": {}
                },
                list_id_3: {
                    "title": "gym",
                    "tasks": {}
                }
            },
            "selected_todolist": list_id_2
        }
        template = app.templates_env.get_template("dashboard.html")
        doc = template.render(user=todolists_user)
        result = self.simulate_post("/get-todolist", cookies={"session-token": self.session_token},
                                    params={"get-todolist": list_id_2})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_updates_selected_todolist_title(self):
        list_id = user_dashboard.create_todolist(self.user_id, "Market")
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

    def test_user_dashboard_deletes_selected_todolist(self):
        list_id_1 = user_dashboard.create_todolist(self.user_id, "my todolist")
        list_id_2 = user_dashboard.create_todolist(self.user_id, "groceries")
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


class TestUserDashboardManagesTasks(testing.TestCase):

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

    def test_on_get_user_dashboard_displays_tasks_of_oldest_created_todolist_if_any(self):
        task_gym_1 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        task_gym_2 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Swimming")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_gym_2: {
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
        doc = template.render(user=todolists_user)
        result = self.simulate_get("/dashboard", cookies={"session-token": self.session_token})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_displays_tasks_of_selected_and_loaded_todolist(self):
        task_gym_1 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        task_gym_2 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Swimming")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_gym_2: {
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
        doc = template.render(user=todolists_user)
        result = self.simulate_post("/get-todolist", cookies={"session-token": self.session_token},
                                    params={"get-todolist": self.gym_list_id})
        self.maxDiff = None
        self.assertEqual(doc, result.text)

    def test_user_dashboard_creates_task_on_selected_todolist_when_add_task_button_is_clicked_with_valid_input(self):
        task_gym_1_id = user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_gym_1_id: {
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
        doc = template.render(user=todolists_user)
        truncate_tasks()
        result = self.simulate_post("/create-task", cookies={"session-token": self.session_token},
                                    params={"selected-todolist": self.gym_list_id, "create-task": "Running"})
        with db.conn as conn:
            with conn.cursor() as curs:
                curs.execute("SELECT task_id FROM tasks WHERE list_id = %s AND task = 'Running'", [self.gym_list_id])
                new_task_gym_1_id = curs.fetchone().task_id
        self.assertTrue(task_gym_1_id == new_task_gym_1_id-1)

    def test_user_dashboard_marks_task_as_done_when_done_button_is_pressed(self):
        task_gym_1 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        task_gym_2 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Swimming")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_gym_2: {
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
        doc = template.render(user=todolists_user)
        result = self.simulate_post("/update-task", cookies={"session-token": self.session_token},
                           params={"mark-task-done": f"{self.gym_list_id};{task_gym_2}"})
        self.assertEqual(doc, result.text)

    def test_user_dashboard_maks_task_as_undone_when_undone_button_is_pressed(self):
        task_gym_1 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Running")
        task_gym_2 = user_dashboard.create_task_in_todolist(self.gym_list_id, "Swimming")
        todolists_user = {
            "author": "John Smith",
            "todolists": {
                self.gym_list_id: {
                    "title": "Gym",
                    "tasks": {
                        task_gym_1: {
                            "task": "Running",
                            "done": False
                        },
                        task_gym_2: {
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