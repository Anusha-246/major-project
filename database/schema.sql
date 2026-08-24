PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS branches (
    branch_id TEXT PRIMARY KEY,
    branch_name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    opened_year INTEGER NOT NULL,
    staff_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    account_type TEXT NOT NULL,
    masked_account TEXT NOT NULL,
    account_open_date TEXT NOT NULL,
    tenure_months INTEGER NOT NULL,
    products_count INTEGER NOT NULL,
    credit_score INTEGER NOT NULL,
    occupation TEXT NOT NULL,
    income_band TEXT NOT NULL,
    satisfaction_score REAL NOT NULL,
    complaint_count INTEGER NOT NULL,
    service_request_count INTEGER NOT NULL,
    churn_label INTEGER NOT NULL,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    txn_date TEXT NOT NULL,
    txn_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE IF NOT EXISTS customer_behaviour (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    month_label TEXT NOT NULL,
    txn_frequency INTEGER NOT NULL,
    txn_amount REAL NOT NULL,
    deposits REAL NOT NULL,
    withdrawals REAL NOT NULL,
    atm_usage INTEGER NOT NULL,
    mobile_usage INTEGER NOT NULL,
    internet_usage INTEGER NOT NULL,
    card_usage INTEGER NOT NULL,
    avg_balance REAL NOT NULL,
    digital_engagement REAL NOT NULL,
    complaints INTEGER NOT NULL,
    service_activity INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS customer_engagement (
    customer_id TEXT PRIMARY KEY,
    mobile_logins INTEGER NOT NULL,
    internet_logins INTEGER NOT NULL,
    app_sessions INTEGER NOT NULL,
    last_login_days INTEGER NOT NULL,
    nps_score REAL NOT NULL,
    product_usage_score REAL NOT NULL,
    digital_active INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS behaviour_deviations (
    customer_id TEXT PRIMARY KEY,
    shift_score REAL NOT NULL,
    anomaly_score REAL NOT NULL,
    classification TEXT NOT NULL,
    deviating_attributes TEXT NOT NULL,
    attribute_details TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS churn_predictions (
    customer_id TEXT PRIMARY KEY,
    probability REAL NOT NULL,
    prediction INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    model_name TEXT NOT NULL,
    shap_top TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS customer_value (
    customer_id TEXT PRIMARY KEY,
    current_value REAL NOT NULL,
    predicted_future_value REAL NOT NULL,
    value_at_risk REAL NOT NULL,
    is_high_value INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS customer_segments (
    customer_id TEXT PRIMARY KEY,
    segment_id INTEGER NOT NULL,
    segment_name TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS retention_strategies (
    customer_id TEXT PRIMARY KEY,
    priority TEXT NOT NULL,
    strategy_title TEXT NOT NULL,
    actions TEXT NOT NULL,
    rationale TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    customer_id TEXT,
    branch_id TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    is_best INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_customers_branch ON customers(branch_id);
CREATE INDEX IF NOT EXISTS idx_txn_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_beh_customer ON customer_behaviour(customer_id);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
