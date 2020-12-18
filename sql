CREATE TABLE IF NOT EXISTS users (
    user_id serial primary key,
    name varchar(80) NOT NULL,
    email varchar(254) unique NOT NULL,
    password char(60) NOT NULL,
    verified bool default false);