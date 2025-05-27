DROP TABLE IF EXISTS documents;

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    body TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    groups TEXT NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users (id)
);