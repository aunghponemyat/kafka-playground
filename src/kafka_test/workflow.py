import structlog
from sqlalchemy.exc import (DisconnectionError, OperationalError,
                            StatementError, TimeoutError)
from sqlalchemy.orm import sessionmaker

from kafka_test.database.db_models import Client, ClientSessions, init_db
from kafka_test.models.config import Settings, get_settings

settings: Settings = get_settings()
Session = sessionmaker(bind=init_db(settings.db_dsn))

def model_to_dict(model_instance: Client):
    return {column.name: getattr(model_instance, column.name) for column in model_instance.__table__.columns}

def handle_session_start(client_sessions: ClientSessions, correlation_id, worker):
    global logger
    logger = structlog.get_logger().bind(worker=worker)
    cid = client_sessions.client_id
    mac = client_sessions.client_mac
    ip = client_sessions.client_ip

    new_client = { "client_id": cid, "client_mac": mac, "client_ip": ip }
    try:
        with Session() as db_handler:
            existing_client = db_handler.query(Client).filter(
                Client.client_id == new_client['client_id']
            ).first()

            if existing_client:
                for key, value in new_client.items():
                    setattr(existing_client, key, value)
                event = "Update client"
                client = existing_client
            else:
                db_handler.add(new_client)
                event = "Create new client"
                client = Client(**new_client)
            db_handler.commit()
            
            client = model_to_dict(client)
            logger.info(event, message="Success", correlation_id=correlation_id, payload=client)
    except (DisconnectionError, TimeoutError, StatementError, OperationalError) as e:
        logger.info("Manage Client", message="Failed", correlation_id=correlation_id, reason=str(e))
    except Exception as e:
        logger.info("Manage Client", message="Failed", correlation_id=correlation_id, reason=str(e))


    
        