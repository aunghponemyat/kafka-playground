import re
from datetime import datetime
from enum import Enum
from typing import Optional

from netaddr import EUI
from pydantic import BaseModel, Field, field_validator, model_validator

from kafka_test.datatypes import MACAddress, valid_mac


class Session(BaseModel):
    session_id: Optional[str]
    correlation_id: str
    payload_id: str
    client_id: Optional[str]
    client_mac: str
    client_ip: str
    onu_id: str
    onu_sn: str
    pon_id: str
    relay_agent_mac: str
    relay_agent_ip: str
    end_reason: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

class ClientSubscription(BaseModel):
    plan_id: str
    client_id: str
    package_id: str
    status: str

class EventMsg(BaseModel):
    event: str
    hwaddr: str
    hops: Optional[int] = None
    lease4addr: Optional[str] = None
    lease4cltt: Optional[int] = None
    lease4validlft: Optional[int] = None
    localaddr: Optional[str] = None
    localport: Optional[int] = None
    opt55: Optional[str] = None
    opt60: Optional[str] = None
    opt82sub1: Optional[str] = None
    opt82sub2: Optional[str] = None
    relayed: Optional[bool] = None
    remoteaddr: Optional[str] = None
    remoteport: Optional[int] = None
    hash_value: Optional[str] = None

    @field_validator("hwaddr")
    def validate_and_convert_hwaddr(cls, v):
        if isinstance(v, MACAddress):
            return str(EUI(v))
        if not valid_mac(v):
            raise ValueError("invalid MAC address format")
        return str(EUI(v))

class SessionBinder(BaseModel):
    event_type: str
    client_id: str
    client_ip: Optional[str] = None
    client_mac: Optional[str] = None
    onu_id: Optional[str] = None
    onu_serial: Optional[str] = None
    pon_id: Optional[str] = None
    relay_agent_mac: Optional[str] = None
    relay_agent_ip: Optional[str] = None
    bw_speed: Optional[float] = None
    service_type: Optional[str] = None
    is_byte_counting: Optional[bool] = None

class KoreBinder(BaseModel):
    event_type: str
    client_id: str
    bw_speed: float
    service_type: str
    is_byte_counting: Optional[bool] = None

class Redir(BaseModel):
    ipAddress: str
    macAddress: str

class SessionBase(BaseModel):
    sessionId: str

class UnclosedSession(BaseModel):
    clientState: int
    uid: str
    redir: Redir
    session: SessionBase

class PolicyEnforce(BaseModel):
    onu_id: str
    onu_sn: str
    onu_hostname: str
    pon_id: str
    olt_mac: str
    olt_ip: str

    @model_validator(mode="after")
    def __validate_model(self):
        pattern = '([A-Z]{2,3}[0-9]{6})'
        if not re.findall(pattern, self.onu_hostname):
            raise ValueError("Invalid hostname format")
        return self

class EventTypes(Enum):
    committed = "COMMITTED"
    expire = "EXPIRE"
    decline = "DECLINE"
    release = "RELEASE"
    recover = "RECOVER"
    renew = "RENEW"
