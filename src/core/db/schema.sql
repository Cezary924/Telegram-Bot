CREATE TABLE IF NOT EXISTS bot_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    role INTEGER NOT NULL DEFAULT 0,
    has_consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    language TEXT NOT NULL DEFAULT 'en',
    has_notifications INTEGER NOT NULL DEFAULT 1,
    has_admin_alerts INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_screens (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    module TEXT NOT NULL,
    view TEXT NOT NULL,
    argument TEXT,
    message_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_screen_arguments (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module TEXT NOT NULL,
    view TEXT NOT NULL,
    argument TEXT,
    PRIMARY KEY (user_id, module, view)
);

DROP TABLE IF EXISTS user_navigation_stacks;
DROP TABLE IF EXISTS user_anchors;

CREATE TABLE IF NOT EXISTS user_module_state (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (user_id, module, key)
);
