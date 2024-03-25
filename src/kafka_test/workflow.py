from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    StatementError,
    TimeoutError
)
import json
import structlog

from kafka_test.database.db_models import ClientSessions, Client, init_db
from kafka_test.models.config import Settings, get_settings
from kafka_test.eventlog import logger

settings: Settings = get_settings()
session = sessionmaker(bind=init_db(settings.tidb_dsn))

def handle_session_start(client_sessions: ClientSessions, correlation_id, worker):
    global logger
    logger = structlog.get_logger().bind(worker=worker)
    cid = client_sessions.client_id
    mac = client_sessions.client_mac
    ip = client_sessions.client_ip

    new_client = { "client_id": cid, "client_mac": mac, "client_ip": ip }
    try:
        with session() as db_handler:
            existing_client = db_handler.query(Client).filter(
                Client.client_id == cid
            ).first()

            if existing_client:
                for key, value in new_client.items():
                    setattr(existing_client, key, value)
                event = "Update client"
            else:
                db_handler.add(new_client)
                event = "Create new client"
            db_handler.commit()
            logger.info(event, message="Success", correlation_id=correlation_id, payload=json.dumps(existing_client or new_client))
    except (DisconnectionError, TimeoutError, StatementError, OperationalError) as e:
        logger.info("Manage Client", message="Failed", correlation_id=correlation_id, reason=str(e))
    except Exception as e:
        logger.info("Manage Client", message="Failed", correlation_id=correlation_id, reason=str(e))


    
        