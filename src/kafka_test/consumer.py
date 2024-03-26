import json
from datetime import datetime

from kafka import ConsumerRebalanceListener, KafkaConsumer
from kafka.errors import KafkaConnectionError, TopicAuthorizationFailedError
from sqlalchemy.orm import sessionmaker

from kafka_test.database.db_models import ClientSessions, PayloadMsg, init_db
from kafka_test.eventlog import logger
# from lts.kore_workflow import handle_session_start, send_to_binder
from kafka_test.models.config import Settings, get_settings
from kafka_test.models.dhcp_models import EventTypes as ET
from kafka_test.utils import (compute_hash, decode_hexastr, generate_uuid4,
                              mac2EUI, parse_properties)
from kafka_test.workflow import handle_session_start

settings: Settings = get_settings()
Session = sessionmaker(bind=init_db(settings.db_dsn))

class Rebalance(ConsumerRebalanceListener):
    def __init__(self, logger):
        self.logger = logger

    def on_partitions_assigned(self, assigned):
        for tp in assigned:
            self.logger.info("Assigned Partition", message=f"Consumer is assigned to partition: {tp.partition}")
        return super().on_partitions_assigned(assigned)

    def on_partitions_revoked(self, revoked):
        for tp in revoked:
            self.logger.info("Revoked Partition", message=f"Consumer is revoked from partition: {tp.partition}")
        return super().on_partitions_revoked(revoked)

def process_message(message, worker):
    event_msg: dict = message.value
    event_type = event_msg.get("event")

    if event_type != ET.committed.value:
        handle_session_end(event_msg)
        return

    opt82sub1 = event_msg.get("opt82sub1")
    opt82sub2 = event_msg.get("opt82sub2")

    if not opt82sub1 or not opt82sub2:
        logger.info('Incomplete payload message', message='Payload message not complete! Skipping...')
        return
    
    handle_committed_event(event_msg, worker)

def extract_metadata_fields(metadata: PayloadMsg) -> tuple:
    cid = None
    if metadata.opt60 and metadata.opt60 is not None:
        decoded_opt60 = decode_hexastr(metadata.opt60)
        cid = decoded_opt60.split(":")[1] if ":" in decoded_opt60 else None

    if metadata.opt82sub1:
        decoded_opt82sub1 = decode_hexastr(metadata.opt82sub1)
        components = decoded_opt82sub1.split("/") if "/" in decoded_opt82sub1 else None
        pon_id = components[1]
        onu_id = components[2]
        onu_sn = components[3]

    relay_agent_mac = None
    if metadata.opt82sub2:
        relay_agent_mac = mac2EUI(decode_hexastr(metadata.opt82sub2))
    relay_agent_ip = metadata.remoteaddr

    return cid, onu_id, onu_sn, pon_id, relay_agent_mac, relay_agent_ip


def handle_committed_event(event_msg: dict, worker: str):
    hashed_value = compute_hash(event_msg)
    with Session() as session:
        data = session.query(PayloadMsg.payload_id).filter(PayloadMsg.hash_value == hashed_value).first()
        existing_hash = data[0] if data else None
        if existing_hash:
            logger.info(
                event_msg.get("event"),
                message="Same hash exists! Skipping...",
                payload=json.dumps(event_msg),
            )
        else:
            event_msg["hwaddr"] = mac2EUI(event_msg.get("hwaddr"))
            metadata = PayloadMsg(payload_id=generate_uuid4(), **event_msg)
            cid, onu_id, onu_sn, pon_id, relay_agent_mac, relay_agent_ip = extract_metadata_fields(metadata)

            client_sessions = ClientSessions(
                session_id=generate_uuid4(),
                payload_id=metadata.payload_id,
                correlation_id=generate_uuid4(),
                client_id=cid,
                client_mac=mac2EUI(event_msg.get("hwaddr")),
                client_ip=event_msg.get("lease4addr"),
                onu_id=onu_id,
                onu_sn=onu_sn,
                pon_id=pon_id,
                relay_agent_mac=relay_agent_mac,
                relay_agent_ip=relay_agent_ip
            )
            correlation_id = client_sessions.correlation_id
            logger.info(
                event_msg.get("event"),
                correlation_id=correlation_id,
                message="New Payload",
                payload=json.dumps(event_msg),
            )
            metadata.hash_value = hashed_value
            invalidate_old_session(client_sessions.client_mac)
            session.add(metadata)
            session.commit()

            existing_payload = session.query(PayloadMsg).filter(
                PayloadMsg.payload_id == metadata.payload_id
            ).first()
            if existing_payload:
                session.add(client_sessions)
                session.commit()
                handle_session_start(client_sessions, correlation_id, worker)
            else:
                logger.info("Duplicate data", message="Duplicate message skipped!")

def invalidate_old_session(mac: str):
    with Session() as session:
        try:
            old_session = session.query(ClientSessions).filter(
                ClientSessions.client_mac == mac,
                ClientSessions.end_reason.is_(None),
                ClientSessions.end_time.is_(None)
            ).first()
            if old_session:
                old_session.end_reason = "INVALIDATED"
                old_session.end_time = datetime.utcnow()
                session.commit()

                session.refresh(old_session)
                logger.info(
                    "INVALIDATED",
                    correlation_id=old_session.correlation_id,
                    message="Session ended",
                )
                session.commit()
        except Exception as e:
            logger.info(
                "Error in invalidate_old_session",
                client_mac=mac,
                error_message=str(e),
            )
            raise

def handle_session_end(event_msg: dict):
    with Session() as session:
        ongoing_session = session.query(ClientSessions).filter(
            ClientSessions.client_mac == mac2EUI(event_msg.get("hwaddr")),
            ClientSessions.client_ip == event_msg.get("lease4addr"),
            ClientSessions.end_reason.is_(None),
            ClientSessions.end_time.is_(None)
        ).first()

        if ongoing_session:
            ongoing_session.end_reason = event_msg["event"]
            ongoing_session.end_time = datetime.utcnow()

            correlation_id = ongoing_session.correlation_id
            logger.info(
                event_msg.get("event"),
                correlation_id=correlation_id,
                message="Session ended",
                payload=json.dumps(event_msg)
            )
            session.commit()
        else:
            logger.info(
                event_msg.get("event"),
                message="No matching session found",
                payload=json.dumps(event_msg)
            )

def connect_plain_broker(topic, kafka_config: dict): 
    kafka_config.pop("security_protocol", None) 
    kafka_config.pop("sasl_mechanism", None) 
    kafka_config.pop("sasl_plain_username", None) 
    kafka_config.pop("sasl_plain_password", None) 
    kafka_config.pop("topic", None)
    return KafkaConsumer(topic, **kafka_config)

def initiate_consumer(consumer: KafkaConsumer, worker: str):
    if not consumer:
        print("Consumer is not initialized.")
        return

    while True:
        try:
            for message in consumer: 
                process_message(message, worker) 
        except KafkaConnectionError as e: 
            print(f"Connection to broker lost: {e}") 
            raise
        except Exception as e:
            print(f"Error: {e}")
            pass
        except KeyboardInterrupt: 
            break
    if consumer:
        consumer.close() 

def create_kafka_consumer(worker): 
    kafka_config = parse_properties(settings.properties_file) 
    broker_list = kafka_config.get("bootstrap_servers", "").split(",") 
    kafka_config["value_deserializer"] = json.loads 
    kafka_config.pop("bootstrap_servers") 
    try_broker(broker_list, kafka_config, worker)
    return

def try_broker(broker_list, kafka_config, worker): 
    consumer = None 
    try: 
        temp_config = kafka_config.copy()
        topic = temp_config['topic']
        temp_config["bootstrap_servers"] = broker_list 
        consumer = connect_plain_broker(topic, temp_config)
        if consumer:
            listener = Rebalance(logger)
            consumer.subscribe([topic], listener=listener)
            consumer.poll(timeout_ms=1000)
            initiate_consumer(consumer, worker)
            return True

        else:
            return False
    except TopicAuthorizationFailedError as e: 
        print(f"Error: {e}") 
    except KafkaConnectionError as e: 
        print(e) 
        return False
    finally:
        if consumer:
            consumer.close() 

def initialize(worker: str):
    global logger
    create_kafka_consumer(worker)
 
