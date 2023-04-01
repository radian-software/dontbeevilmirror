from contextlib import contextmanager
import dataclasses
import datetime
import os

import psycopg2.extras
import psycopg2.pool

from dontbeevilmirror.api import Credentials

database_url = os.environ["DATABASE_URL"]
if "${POSTGRES_PASSWORD}" in database_url:
    database_url = database_url.replace(
        "${POSTGRES_PASSWORD}", os.environ["POSTGRES_PASSWORD"]
    )

pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=0,
    maxconn=5,
    dsn=database_url,
    cursor_factory=psycopg2.extras.DictCursor,
)


@contextmanager
def connection():
    conn = pool.getconn()
    try:
        with conn:
            yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def cursor():
    with connection() as conn:
        with conn.cursor() as curs:
            yield curs


def now() -> datetime.datetime:
    return datetime.datetime.now()


def set_credentials(curs, creds: Credentials):
    curs.execute(
        "INSERT INTO google_play_authentication (create_ts, format_version, auth_data) VALUES (%(create_ts)s, %(format_version)s, %(auth_data)s)",
        {
            "create_ts": now(),
            "format_version": 1,
            "auth_data": dataclasses.asdict(creds),
        },
    )


def get_credentials(curs) -> Credentials | None:
    curs.execute(
        "SELECT auth_data FROM google_play_authentication WHERE format_version = 1 ORDER BY create_ts DESC"
    )
    if obj := curs.fetchone():
        return Credentials.fromdict(obj["auth_data"])
