CREATE TABLE IF NOT EXISTS users (
    user_id serial primary key,
    username varchar(30) unique,
    email varchar(254) unique,
    password char(60),
    verified bool default false);