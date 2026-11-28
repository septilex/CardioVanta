-- Non-clinical accounts and operational metadata only.
CREATE TABLE users (
    id UUID PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE,
    password_hash TEXT, active BOOLEAN NOT NULL DEFAULT TRUE,
    token_version INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE roles (name VARCHAR(20) PRIMARY KEY CHECK (name IN ('viewer','researcher','admin')));
INSERT INTO roles (name) VALUES ('viewer'), ('researcher'), ('admin');
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_name VARCHAR(20) NOT NULL REFERENCES roles(name), PRIMARY KEY(user_id, role_name)
);
CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL, subject VARCHAR(255) NOT NULL, UNIQUE(provider, subject)
);
CREATE TABLE refresh_sessions (
    id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family UUID NOT NULL, token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL, consumed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX refresh_sessions_expiry_idx ON refresh_sessions(expires_at);
CREATE INDEX refresh_sessions_family_idx ON refresh_sessions(family);
CREATE INDEX refresh_sessions_user_idx ON refresh_sessions(user_id);
CREATE TABLE oauth_flows (
    token_hash CHAR(64) PRIMARY KEY, payload TEXT NOT NULL,
    link_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX oauth_flows_expiry_idx ON oauth_flows(expires_at);
CREATE TABLE upload_batches (
    id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL CHECK(status IN ('ready','validating','importing','completed','failed')),
    row_count INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX upload_batches_owner_idx ON upload_batches(user_id, created_at);
CREATE TABLE support_payments (
    id UUID PRIMARY KEY, request_key VARCHAR(64) NOT NULL UNIQUE,
    amount INTEGER NOT NULL CHECK(amount IN (500,1000,2500)),
    checkout_id VARCHAR(255) UNIQUE, status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE payment_events (
    event_id VARCHAR(255) PRIMARY KEY, payment_id UUID NOT NULL REFERENCES support_payments(id),
    event_type VARCHAR(80) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE maintenance_runs (
    run_date DATE PRIMARY KEY, removed_sessions INTEGER NOT NULL, completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
