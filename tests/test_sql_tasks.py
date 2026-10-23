# Прогоняю решения из sql/tasks на тестовых данных и сверяю с ожидаемым.
# Схема и данные создаются в транзакции, в конце rollback - база не меняется.
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

SQL_DIR = Path(__file__).parent.parent / "sql"


@pytest.fixture
def cur(db_params):
    with psycopg.connect(**db_params) as conn:
        cur = conn.cursor()
        cur.execute((SQL_DIR / "01_schema.sql").read_text(encoding="utf-8"))
        cur.execute((SQL_DIR / "02_seed.sql").read_text(encoding="utf-8"))
        yield cur
        conn.rollback()


def run(cur, name):
    cur.execute((SQL_DIR / "tasks" / name).read_text(encoding="utf-8"))
    return cur.fetchall()


def test_task1(cur):
    rows = run(cur, "01_simple_select.sql")
    assert [r[0] for r in rows] == [2, 1, 7]


def test_task2(cur):
    rows = run(cur, "02_open_accounts_by_currency.sql")
    assert rows == [("CNY", 1), ("EUR", 1), ("RUB", 6), ("USD", 1)]


def test_task3(cur):
    rows = run(cur, "03_incoming_total_by_client.sql")
    assert {r[0]: r[2] for r in rows} == {
        1: Decimal("12000"), 2: Decimal("8001"), 3: Decimal("3000"), 4: Decimal("800"),
        5: 0, 6: 0, 7: 0, 8: 0,
    }


def test_task4(cur):
    rows = run(cur, "04_clients_without_accounts.sql")
    assert [r[0] for r in rows] == [6, 8]


def test_task5(cur):
    rows = run(cur, "05_clients_with_more_than_two_accounts.sql")
    assert [(r[0], r[2]) for r in rows] == [(3, 4), (1, 3)]


def test_task6(cur):
    rows = run(cur, "06_duplicate_transactions.sql")
    assert [(r[0], r[1], r[3], r[4]) for r in rows] == [
        (101, datetime(2025, 5, 10, 8, 15), 3, [8, 9, 10]),
        (104, datetime(2025, 5, 1, 12, 0), 2, [3, 4]),
    ]


def test_task7(cur):
    rows = run(cur, "07_top3_outgoing_by_month.sql")
    assert [(r[0], r[2]) for r in rows] == [
        (date(2025, 5, 1), 1), (date(2025, 5, 1), 2), (date(2025, 5, 1), 4),
        (date(2025, 6, 1), 3), (date(2025, 6, 1), 4), (date(2025, 6, 1), 1),
        (date(2025, 7, 1), 2), (date(2025, 7, 1), 4), (date(2025, 7, 1), 1),
    ]
