DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS clients;

CREATE TABLE clients (
    client_id     integer PRIMARY KEY,
    full_name     text NOT NULL,
    city          text,
    registered_at date NOT NULL
);

CREATE TABLE accounts (
    account_id integer PRIMARY KEY,
    client_id  integer NOT NULL REFERENCES clients (client_id),
    currency   char(3) NOT NULL,
    opened_at  date NOT NULL,
    closed_at  date,
    CHECK (closed_at IS NULL OR closed_at >= opened_at)
);

CREATE TABLE transactions (
    tx_id      integer PRIMARY KEY,
    account_id integer NOT NULL REFERENCES accounts (account_id),
    tx_date    timestamp NOT NULL,
    amount     numeric(18, 2) NOT NULL CHECK (amount > 0),
    tx_type    text NOT NULL CHECK (tx_type IN ('in', 'out'))
);

-- на FK постгрес индексы сам не создаёт
CREATE INDEX ON accounts (client_id);
CREATE INDEX ON transactions (account_id, tx_date);
