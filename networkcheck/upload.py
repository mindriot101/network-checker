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
from .runs_ping import RunsPing
from .logging import logger


DEFAULT_HOST = "93.184.216.34"


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

    with Database(args.output, clear=args.reset) as database:
        results = RunsPing.perform(host=args.host, number=args.number)
        database.upload_results(results)


if __name__ == "__main__":
    main()
