import os

import pytest


@pytest.fixture(scope="session")
def db_params():
    # по умолчанию - то, что в docker-compose.yml
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "bank"),
        "user": os.getenv("DB_USER", "intern"),
        "password": os.getenv("DB_PASSWORD", "intern_pass"),
        "connect_timeout": 5,
    }
