import pytest
from networkcheck.runs_ping import RunsPing, SummaryResult, PingResult
from typing import NamedTuple


@pytest.fixture
def macos_process():
    stdout = b"""PING 93.184.216.34 (93.184.216.34): 56 data bytes
64 bytes from 93.184.216.34: icmp_seq=0 ttl=53 time=91.755 ms

--- 93.184.216.34 ping statistics ---
1 packets transmitted, 1 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 91.755/91.755/91.755/0.000 ms"""

    return MockCompletedProcess(stdout=stdout)


@pytest.fixture
def rpi_output():
    stdout = b"""PING 93.184.216.34 (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34: icmp_seq=1 ttl=53 time=94.0 ms

--- 93.184.216.34 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 94.017/94.017/94.017/0.000 ms"""

    return MockCompletedProcess(stdout=stdout)


class MockCompletedProcess(NamedTuple):
    stdout: bytes


class TestOutputParsing(object):
    def test_parse_macos_output(self, macos_process):
        expected = {
            "status": "success",
            "pings": [
                PingResult(nbytes=64, ip_addr="93.184.216.34", icmp_seq=0,
                    ttl=53, time_ms=91.755),
            ],
            "summary": SummaryResult(n_transmitted=1, n_received=1, packet_loss=0.0),
        }

        assert RunsPing.successful_pings(macos_process) == expected

    def test_parse_rpi_output(self, rpi_output):
        expected = {
            "status": "success",
            "pings": [
                PingResult(nbytes=64, ip_addr="93.184.216.34", icmp_seq=1,
                    ttl=53, time_ms=94.0),
            ],
            "summary": SummaryResult(n_transmitted=1, n_received=1, packet_loss=0.0),
        }

        assert RunsPing.successful_pings(rpi_output) == expected

