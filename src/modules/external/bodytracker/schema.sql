CREATE TABLE IF NOT EXISTS module_bodytracker_weights (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weight REAL NOT NULL,
    measured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module_bodytracker_heights (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    height REAL NOT NULL,
    measured_at TEXT NOT NULL
);
