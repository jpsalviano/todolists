CREATE TABLE IF NOT EXISTS users (
    user_id serial primary key,
    name varchar(80),
    email varchar(254) unique,
    password char(60),
    verified bool default false);