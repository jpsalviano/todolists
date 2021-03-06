CREATE TABLE IF NOT EXISTS users (
    user_id serial PRIMARY KEY,
    name varchar(80) NOT NULL,
    email varchar(254) UNIQUE NOT NULL,
    password char(60) NOT NULL,
    verified bool DEFAULT false);

CREATE TABLE IF NOT EXISTS lists (
    list_id serial PRIMARY KEY,
    title varchar(50) NOT NULL,
    user_id integer NOT NULL,
    UNIQUE (title, user_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id));

CREATE TABLE IF NOT EXISTS tasks (
    task_id serial PRIMARY KEY,
    task varchar(500) NOT NULL,
    done bool DEFAULT false,
    list_id integer NOT NULL
    FOREIGN KEY(list_id) REFERENCES lists(list_id));
