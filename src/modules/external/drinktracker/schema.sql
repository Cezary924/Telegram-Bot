CREATE TABLE IF NOT EXISTS module_drinktracker_drinks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    volume REAL NOT NULL,
    strength REAL NOT NULL,
    grams REAL NOT NULL,
    kcal REAL NOT NULL,
    food TEXT,
    drunk_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module_drinktracker_sizes (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    height REAL NOT NULL,
    weight REAL NOT NULL
);
