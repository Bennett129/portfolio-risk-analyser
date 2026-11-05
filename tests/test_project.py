import socket

import pytest
from pytest_socket import SocketBlockedError

import riskanalyser


def test_package_exposes_version() -> None:
    assert riskanalyser.__version__ == "0.1.0"


@pytest.mark.filterwarnings("ignore:A test tried to use socket")
def test_network_access_is_blocked_during_tests() -> None:
    with pytest.raises(SocketBlockedError):
        socket.socket()
