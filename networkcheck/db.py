from typing import List, Any, Generator
import sqlite3
import uuid
import datetime
from contextlib import contextmanager
from .types import PingSummary
from .logging import logger
import math


def std(*values):
    n = len(values)
    if n == 0:
        return 0.0

    meanval = 0.0
    for val in values:
        meanval += val
    meanval /= n

    stdval = 0.0
    for val in values:
        stdval += (val - meanval) ** 2
    return math.sqrt(stdval / n)


class Std(object):
    def __init__(self):
        self.values = []

    def step(self, value):
        self.values.append(value)

    def finalize(self):
        result = std(*self.values)
        return result


class Database(object):
    def __init__(self, filename: str, clear: bool = False, create: bool = True):
        self.filename = filename
        self.clear = clear
        self.create = create

    def __enter__(self) -> "Database":
        logger.debug("creating database %s", self.filename)
        self.connection = sqlite3.connect(self.filename)
        if self.clear:
            self.reset()
        if self.create:
            self.setup()
        self.connection.create_function("sqrt", 1, math.sqrt)
        self.connection.create_aggregate("std", 1, Std)
        return self

    def __exit__(self, *args: List[Any]) -> None:
        self.connection.close()

    def setup(self) -> None:
        logger.info("initialising database")
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON")
            self.create_tables(cursor)

    def reset(self) -> None:
        logger.info("resetting database")
        with self.cursor() as cursor:
            for table_name in "session", "pings", "summary":
                self.drop_table(cursor, table_name)

    def drop_table(self, cursor: sqlite3.Cursor, table_name: str) -> None:
        logger.info("dropping table %s", table_name)
        cursor.execute("""drop table {}""".format(table_name))

    def create_tables(self, cursor: sqlite3.Cursor) -> None:
        logger.info("creating tables")
        cursor.execute(
            """create table if not exists session (
        id string primary key,
        created integer not null
        )"""
        )
        cursor.execute(
            """create table if not exists pings (
        id integer primary key,
        session_id string not null,
        nbytes integer not null,
        ip_addr string not null,
        icmp_seq integer not null,
        time_ms real not null,
        foreign key(session_id) references session(id)
        )"""
        )
        cursor.execute(
            """create table if not exists summary (
            id integer primary key,
            session_id string not null,
            n_transmitted integer not null,
            n_received integer not null,
            packet_loss real not null,
            foreign key(session_id) references session(id)
        )"""
        )

    def upload_results(self, results: PingSummary) -> None:
        with self.cursor() as cursor:
            session_id = str(uuid.uuid4())
            created = datetime.datetime.now()

            # Session
            logger.info("uploading session")
            cursor.execute(
                """insert into session (id, created) values (?, ?)""",
                (session_id, created.timestamp()),
            )

            # Pings
            logger.info("uploading pings")
            for ping in results["pings"]:
                cursor.execute(
                    """insert into pings (session_id, nbytes,
                        ip_addr, icmp_seq, time_ms) values (?, ?, ?, ?,
                        ?)""",
                    (
                        session_id,
                        ping.nbytes,
                        ping.ip_addr,
                        ping.icmp_seq,
                        ping.time_ms,
                    ),
                )

            # Summary
            summary = results["summary"]
            logger.info("uploading summary")
            cursor.execute(
                """insert into summary (session_id, n_transmitted,
                    n_received, packet_loss) values (?, ?, ?, ?)""",
                (
                    session_id,
                    summary.n_transmitted,
                    summary.n_received,
                    summary.packet_loss,
                ),
            )

    def response_times(self, limit: int = None) -> Any:
        with self.cursor() as cursor:
            query = """
            select created, avg(time_ms), std(time_ms) / sqrt(count(time_ms)) as std_err
                    from pings
                    join session on (pings.session_id = session.id)
                    group by pings.session_id
                    order by created asc
                    """
            if limit is not None:
                query += "limit {}".format(int(limit))

            cursor.execute(query)
            return cursor.fetchall()

    def gaps(self, limit: int = None) -> Any:
        with self.cursor() as cursor:
            query = """
            select distinct(created) from session
                    order by created asc
                    """
            if limit is not None:
                query += "limit {}".format(int(limit))

            cursor.execute(query)
            results = cursor.fetchall()

        out = []
        current = results[0][0]
        for t in results[1:]:
            dt = t[0] - current
            out.append((t[0], dt))
            current = t[0]

        return out

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        transaction_id = uuid.uuid4()
        logger.debug("starting transaction %s", transaction_id)
        with self.connection as conn:
            cursor = conn.cursor()
            yield cursor
            logger.debug("ending transaction %s", transaction_id)
