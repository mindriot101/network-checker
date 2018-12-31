from typing import Any, NamedTuple, Match


PingSummary = Any  # TODO


PingResultBase = NamedTuple(
    "PingResultBase",
    [
        ("nbytes", int),
        ("ip_addr", str),
        ("icmp_seq", int),
        ("ttl", int),
        ("time_ms", float),
    ],
)


class PingResult(PingResultBase):
    @classmethod
    def from_matchresult(cls, match: Match[str]) -> "PingResult":
        return cls(
            nbytes=int(match.group("nbytes")),
            ip_addr=match.group("ip_addr"),
            icmp_seq=int(match.group("icmp_seq")),
            ttl=int(match.group("ttl")),
            time_ms=float(match.group("time_ms")),
        )


SummaryResultBase = NamedTuple(
    "SummaryResultBase",
    [("n_transmitted", int), ("n_received", int), ("packet_loss", float)],
)


class SummaryResult(SummaryResultBase):
    @classmethod
    def from_matchresult(cls, match: Match[str]) -> "SummaryResult":
        n_transmitted = int(match.group("n_transmitted"))
        n_received = int(match.group("n_received"))
        packet_loss = float(n_transmitted - n_received) / (n_transmitted)
        return cls(
            n_transmitted=n_transmitted, n_received=n_received, packet_loss=packet_loss
        )
