CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'premium')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    property_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    price REAL NOT NULL,
    down_payment REAL NOT NULL,
    rental_income REAL NOT NULL,
    monthly_expenses REAL NOT NULL,
    cash_flow REAL NOT NULL,
    cash_on_cash_return REAL NOT NULL,
    capitalization_rate REAL NOT NULL,
    debt_service_coverage_ratio REAL NOT NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0 CHECK(is_favorite IN (0, 1)),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS analyses_by_user_created
ON analyses(user_id, created_at DESC);
