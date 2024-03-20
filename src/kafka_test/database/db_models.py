from datetime import datetime

import pymysql
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils import create_database, database_exists

from kafka.models.config import Settings, get_settings

settings: Settings = get_settings()

Base = declarative_base()

class PayloadMsg(Base):
    __tablename__ = "payload_messages"

    payload_id = Column(String(255), primary_key=True)
    event = Column(String(255), nullable=False)
    hwaddr = Column(String(255), nullable=False)
    hops = Column(Integer, nullable=True) 
    lease4addr = Column(String(255), nullable=False) 
    lease4cltt = Column(Integer) 
    lease4validlft = Column(Integer) 
    localaddr = Column(String(255), nullable=True) 
    localport = Column(Integer, nullable=True) 
    opt55 = Column(String(255), nullable=True) 
    opt60 = Column(String(255), nullable=True) 
    opt82sub1 = Column(String(255), nullable=True) 
    opt82sub2 = Column(String(255), nullable=True) 
    relayed = Column(Boolean, nullable=True) 
    remoteaddr = Column(String(255), nullable=True) 
    remoteport = Column(Integer, nullable=True) 
    hash_value = Column(String(255), nullable=False) 

class ClientSessions(Base):
    __tablename__ = "client_sessions"

    session_id = Column(String(255), primary_key=True)
    correlation_id = Column(String(255))
    payload_id = Column(String(255), nullable=False)
    client_id = Column(String(20), nullable=True)
    client_mac = Column(String(20))
    client_ip = Column(String(20))
    onu_id = Column(String(20))
    onu_sn = Column(String(20))
    pon_id = Column(String(20))
    relay_agent_mac = Column(String(20))
    relay_agent_ip = Column(String(20))
    end_reason = Column(String(255), default=None)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

class Client(Base):
    __tablename__ = "client"

    client_id = Column(String(255), primary_key=True)
    client_mac = Column(String(20), nullable=False)
    client_ip = Column(String(20), nullable=False)

class Service(Base):
    __tablename__ = "service"

    package_id = Column(Integer, primary_key=True)
    service_id = Column(String(255))
    installation_id = Column(String(255))
    max_speed = Column(Float, nullable=False)
    min_speed = Column(Float, nullable=False)
    speed_qualifier = Column(String(255))
    tc_reference_id = Column(String(255))
    offpeak = Column(Integer)
    multiplier_ignore = Column(Integer)
    interim_interval = Column(Integer)
    multiplier_index_value = Column(Integer)
    is_high_speed = Column(Boolean)
    service_name = Column(String(255), default='N/A')
    installation_name = Column(String(255), default='N/A')
    installation_category = Column(String(255), default='N/A')

class Subscription(Base):
    __tablename__ = "subscriptions"

    plan_id = Column(String(255), primary_key=True)
    client_id = Column(String(255), nullable=False)
    package_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)

def init_db(dsn: str):
    try:
        engine = create_engine(
            dsn,
            pool_pre_ping=True,
            pool_recycle=settings.tidb_pool_recycle,
            connect_args={
                "read_timeout": settings.tidb_read_timeout,
                "write_timeout": settings.tidb_write_timeout
            }
        )
        if not database_exists(engine.url):
            create_database(engine.url)

        Base.metadata.create_all(engine)
        return engine
    except OperationalError as e:
        print(f"Error: {e}")
        pass
    except pymysql.err.OperationalError as e:
        print(f"Error: {e}")
        pass
