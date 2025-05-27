DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email_address TEXT UNIQUE NOT NULL,
    user_group TEXT,
    password TEXT NOT NULL,
    salt TEXT NOT NULL
);