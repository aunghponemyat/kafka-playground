import re
from ipaddress import IPv4Address, ip_address
from typing import Dict, NamedTuple, Union

from netaddr import EUI, valid_mac
from pydantic import UUID4

# the regex pattern does not need to match exactly for IP address because it will be validated by the IP address data type
socketaddr_pattern = re.compile(
    r"(?P<proto>tcp)://(?P<ipaddr>[0-9|\.|:|localhost]*):(?P<port>[0-9]+)"
)


class SocketAddress(str):
    """Data Structure for Socket Address. Only TCP is supported at the moment.
    Format - pro://ip-address:port-number
    Example - tcp://127.0.0.1:8000
    """

    def __new__(cls, v):
        m = socketaddr_pattern.match(v)
        if not m:
            raise ValueError("invalid socket address format")

        proto = m.group("proto").lower()

        try:
            ipaddr = ip_address(m.group("ipaddr"))
            port = int(m.group("port"))
        except ValueError:
            raise

        s = super(SocketAddress, cls).__new__(cls, f"{proto}://{ipaddr}:{port}")
        s.transport = proto
        s.ip_address = ipaddr
        s.port = port
        return s

    @property
    def transport(self) -> str:
        return self._transport

    @transport.setter
    def transport(self, v) -> None:
        self._transport = v

    @property
    def ip_address(self) -> IPv4Address:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, v: IPv4Address) -> None:
        self._ip_address = v

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, v: int) -> None:
        self._port = v

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self) -> str:
        return "NetworkSocket(%s)" % self


class SocketPeer(NamedTuple):
    host: str
    port: int


InstanceIDType = Union[str, UUID4]


class MACAddress(str):
    """EUI-48 MAC address string"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _):
        if not isinstance(v, str):
            raise TypeError("string required")
        elif not valid_mac(v):
            raise ValueError("invalid MAC address format")
        else:
            return cls(str(EUI(v)))

    @classmethod
    def __get_pydantic_json_schema__(cls, field, _):
        return {
            "type": "string",
            "format": "mac-address",
            "examples": ["00-1A-2B-3C-4D-5E"],
        }


GenericDocument = Dict[str, object]
EventData = Union[str, GenericDocument]

class EventAttrs(NamedTuple):
    type: str
    source: str
