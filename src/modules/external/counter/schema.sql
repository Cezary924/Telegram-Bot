CREATE TABLE IF NOT EXISTS module_counter_counters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    step REAL NOT NULL,
    goal REAL,
    period TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module_counter_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    counter_id INTEGER NOT NULL REFERENCES module_counter_counters(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    changed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS module_counter_changes_by_counter ON module_counter_changes (counter_id, changed_at);
