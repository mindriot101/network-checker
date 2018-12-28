#!/usr/bin/env python


import subprocess as sp
from typing import Dict, Match, NamedTuple, Union, List, Any
import re


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
        self.host = host
        self.number = number

    @classmethod
    def perform(cls, host: str = DEFAULT_HOST, number: int = 3) -> PingSummary:
        self = cls(host, number)
        return self.run()

    def run(self) -> PingSummary:
        cmd = ["ping", "-c", str(self.number), self.host]
        result = sp.run(cmd, capture_output=True)
        if result.returncode == 0:
            return self.successful_pings(result)
        else:
            return self.failed_pings(result)

    def successful_pings(self, p: sp.CompletedProcess) -> PingSummary:
        stdout = p.stdout.decode()
        ping_results = []
        summary_result = None
        for line in stdout.split("\n"):
            if not line:
                continue

            # parse the data transmission rate lines
            if "bytes from" in line:
                match = DATA_TRANSMISSION_RE.match(line)
                if not match:
                    raise ValueError(
                        "non-matching line for data transmission line: {}".format(line)
                    )
                ping_result = PingResult.from_matchresult(match)
                ping_results.append(ping_result)

            elif "packets transmitted" in line:
                match = SUMMARY_RE.match(line)
                if not match:
                    raise ValueError(
                        "non-matching line for summary line: {}".format(line)
                    )
                summary_result = SummaryResult.from_matchresult(match)

        return {"pings": ping_results, "summary": summary_result}

    def failed_pings(self, p: sp.CompletedProcess) -> PingSummary:
        return {}


results = RunsPing.perform(number=2)
print(results)
