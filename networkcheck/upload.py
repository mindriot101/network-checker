#!/usr/bin/env python


import subprocess as sp
from typing import Dict, Match, NamedTuple, Union, List, Any, Optional, Generator
import datetime
from contextlib import contextmanager
import uuid
import logging
import re
import sqlite3

from .db import Database
from .types import PingSummary, PingResult, SummaryResult


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("networkcheck")


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
        result = sp.run(cmd, stdout=sp.PIPE)
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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", required=True, help="Database file to save to"
    )
    parser.add_argument(
        "--host", required=False, default=DEFAULT_HOST, help="Host to check"
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

    with Database(logger, args.output, clear=args.reset) as database:
        results = RunsPing.perform(host=args.host, number=args.number)
        database.upload_results(results)


if __name__ == "__main__":
    main()
