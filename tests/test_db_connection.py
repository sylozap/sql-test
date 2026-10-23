from datetime import datetime, timedelta, timezone

import psycopg
import pytest


def test_connection_and_select_now(db_params):
    with psycopg.connect(**db_params) as conn:
        row = conn.execute("select now()").fetchone()

    assert row is not None
    db_now = row[0]
    assert isinstance(db_now, datetime)
    # время сервера должно быть примерно текущим
    assert abs(datetime.now(timezone.utc) - db_now) < timedelta(minutes=1)


def test_wrong_password_is_rejected(db_params):
    params = dict(db_params, password="definitely_wrong")
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(**params)
