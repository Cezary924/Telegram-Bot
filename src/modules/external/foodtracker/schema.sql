CREATE TABLE IF NOT EXISTS module_foodtracker_meals (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kcal REAL NOT NULL,
    eaten_at TEXT NOT NULL
);
