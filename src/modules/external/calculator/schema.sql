CREATE TABLE IF NOT EXISTS module_calculator_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    made_at TEXT NOT NULL
);
