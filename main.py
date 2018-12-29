#!/usr/bin/env python


import subprocess as sp
from typing import Dict, Match, NamedTuple, Union, List, Any, Optional, Generator
import datetime
from contextlib import contextmanager
import uuid
import logging
import re
import sqlite3


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("networkcheck")

PingSummary = Any  # TODO


DEFAULT_HOST = "93.184.216.34"
DATA_TRANSMISSION_RE = re.compile(
    r"""^(?P<nbytes>\d+)\s+                                   # number of bytes
         bytes\s+from\s+
         (?P<ip_addr>(\d{1,3}\.){3}\d{1,3}):\s+
         icmp_seq=(?P<icmp_seq>\d+)\s+
         ttl=(?P<ttl>\d+)\s+
         time=(?P<time_ms>\d+\.\d+)\s+ms$
         """,
    re.X,
)
SUMMARY_RE = re.compile(
    r"""^
    (?P<n_transmitted>\d+)\s+packets\s+transmitted,\s+
    (?P<n_received>\d+)\s+packets\s+received,\s+
        .*$
        """,
    re.X,
)


class PingResult(NamedTuple):
    nbytes: int
    ip_addr: str
    icmp_seq: int
    ttl: int
    time_ms: float

    @classmethod
    def from_matchresult(cls, match: Match[str]) -> "PingResult":
        return cls(
            nbytes=int(match.group("nbytes")),
            ip_addr=match.group("ip_addr"),
            icmp_seq=int(match.group("icmp_seq")),
            ttl=int(match.group("ttl")),
            time_ms=float(match.group("time_ms")),
        )


class SummaryResult(NamedTuple):
    n_transmitted: int
    n_received: int
    packet_loss: float

    @classmethod
    def from_matchresult(cls, match: Match[str]) -> "SummaryResult":
        n_transmitted = int(match.group("n_transmitted"))
        n_received = int(match.group("n_received"))
        packet_loss = float(n_transmitted - n_received) / (n_transmitted)
        return cls(
            n_transmitted=n_transmitted, n_received=n_received, packet_loss=packet_loss
        )


class RunsPing(object):
    def __init__(self, host: str = DEFAULT_HOST, number: int = 3):
        logger.debug("creating RunsPing host=%s number=%s", host, number)
        self.host = host
        self.number = number

    @classmethod
    def perform(cls, host: str = DEFAULT_HOST, number: int = 3) -> PingSummary:
        logger.info("running ping test")
        self = cls(host, number)
        return self.run()

    def run(self) -> PingSummary:
        cmd = ["ping", "-c", str(self.number), self.host]
        logger.info("running command %s", cmd)
        result = sp.run(cmd, capture_output=True)
        if result.returncode == 0:
            return self.successful_pings(result)
        else:
            return self.failed_pings(result)

    def successful_pings(self, p: sp.CompletedProcess) -> PingSummary:
        logger.info("successful ping")
        stdout = p.stdout.decode()
        ping_results = []
        summary_result = None
        for line in stdout.split("\n"):
            if not line:
                continue

            # parse the data transmission rate lines
            if "bytes from" in line:
                logger.debug("found data transmission line")
                match = DATA_TRANSMISSION_RE.match(line)
                if not match:
                    raise ValueError(
                        "non-matching line for data transmission line: {}".format(line)
                    )
                ping_result = PingResult.from_matchresult(match)
                logger.debug("ping result: %s", ping_result)
                ping_results.append(ping_result)

            elif "packets transmitted" in line:
                logger.debug("found summary line")
                match = SUMMARY_RE.match(line)
                if not match:
                    raise ValueError(
                        "non-matching line for summary line: {}".format(line)
                    )
                summary_result = SummaryResult.from_matchresult(match)
                logger.debug("summary result: %s", summary_result)

        return {"status": "success", "pings": ping_results, "summary": summary_result}

    def failed_pings(self, p: sp.CompletedProcess) -> PingSummary:
        return {"status": "failure"}


class Database(object):
    def __init__(self, filename: str, clear: bool = False):
        self.filename = filename
        self.clear = clear

    def __enter__(self) -> "Database":
        logger.debug("creating database %s", self.filename)
        self.connection = sqlite3.connect(self.filename)
        if self.clear:
            self.reset()
        self.setup()
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
        created date not null
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
                (session_id, created),
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

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        transaction_id = uuid.uuid4()
        logger.debug("starting transaction %s", transaction_id)
        with self.connection as conn:
            cursor = conn.cursor()
            yield cursor
            logger.debug("ending transaction %s", transaction_id)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", required=True, help="Database file to save to"
    )
    parser.add_argument(
        "-r",
        "--reset",
        default=False,
        action="store_true",
        help="Reset the database before creating",
    )
    parser.add_argument(
        "-n",
        "--number",
        default=3,
        type=int,
        help="Number of pings to perform for test",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="More verbose logging"
    )
    args = parser.parse_args()

    if args.verbose == 0:
        pass
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose > 1:
        logger.setLevel(logging.DEBUG)

    with Database(args.output, clear=args.reset) as database:
        results = RunsPing.perform(number=args.number)
        database.upload_results(results)


if __name__ == "__main__":
    main()
