import connexion
import yaml
import logging.config
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from vehiclestatus import VehicleStatusEvent
from incidentreport import IncidentEvent
from datetime import datetime
import uuid
import colorlog
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from createdb import create_database
from createtables import create_tables
import os

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yaml"
    log_conf_file = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yaml"
    log_conf_file = "log_conf.yaml"

# [V11] Configuration now externalized to YAML files for improved flexibility
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logger = logging.getLogger('basicLogger')
    logging.config.dictConfig(log_config)

# [V4] KAFKA
logger.info(f"Connecting to MySQL database at {app_config['datastore']['hostname']}:{app_config['datastore']['port']}")
try:
    DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
    Session = sessionmaker(bind=DB_ENGINE)
    logger.info("Database engine and sessionmaker successfully created.")
except Exception as e:
    logger.error(f"Failed to create database engine or sessionmaker: {e}")


# DATABASE ENGINE with pooling options
def get_engine():
    engine = create_engine(
        f"mysql+pymysql://{app_config['datastore']['user']}:" +
        f"{app_config['datastore']['password']}@" +
        f"{app_config['datastore']['hostname']}:" +
        f"{app_config['datastore']['port']}/" +
        f"{app_config['datastore']['db']}",
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,  # seconds
        pool_recycle=3600,  # seconds
        pool_pre_ping=True,
    )
    return engine

DB_ENGINE = get_engine()
Session = sessionmaker(bind=DB_ENGINE)

# Database initialization
create_database()
create_tables()

# [V2] Added trace id and changed the messages to have color 
def reportVehicleStatusEvent(body):
    session = Session()
    try:
        # Ensure trace_id is provided, generate one if not
        if 'trace_id' not in body or not body['trace_id']:
            body['trace_id'] = str(uuid.uuid4())

        # Remove 'datetime' from the body if present
        body.pop('datetime', None)

        new_event = VehicleStatusEvent(**body)
        session.add(new_event)
        session.commit()
        logger.debug(f"Stored Vehicle Status Event response (Id: {body['trace_id']})")
        return 'Vehicle Status Event logged', 201
    
    except Exception as err:
        logger.error(f"Error storing Vehicle Status Event: {err}")
        session.rollback()
        return f"Error processing Vehicle Status Event: {err}", 500
    
    finally:
        session.close()

def reportIncidentEvent(body):
    session = Session()
    try:
        # Ensure trace_id is provided, generate one if not
        if 'trace_id' not in body or not body['trace_id']:
            body['trace_id'] = str(uuid.uuid4())

        # Remove 'datetime' from the body if present
        body.pop('datetime', None)

        new_event = IncidentEvent(**body)
        session.add(new_event)
        session.commit()
        logger.debug(f"Stored Incident Event response (Id: {body['trace_id']})")
        return 'Incident Event logged', 201
    
    except Exception as err:
        logger.error(f"Error storing Incident Event: {err}")
        session.rollback()
        return f"Error processing Incident Event: {err}", 500
    
    finally:
        session.close()

# [V3] \/
def parse_date(timestamp_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):  # Try parsing with and without microseconds
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    raise ValueError("no valid date format found")


def GetreportVehicleStatusEvent(start_timestamp, end_timestamp):
    try:
        start_datetime = parse_date(start_timestamp)
        end_datetime = parse_date(end_timestamp)

        session = Session()
        events = session.query(VehicleStatusEvent).filter(
            VehicleStatusEvent.date_created >= start_datetime,
            VehicleStatusEvent.date_created <= end_datetime
        ).all()
        
        events_list = [event.to_dict() for event in events]
        return events_list, 200
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        return {"error": "Invalid date format provided."}, 400
    except SQLAlchemyError as e:
        logger.error(f"Database query error: {e}")
        return {"error": "An error occurred while fetching vehicle status events."}, 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "An unexpected error occurred."}, 500
    finally:
        session.close()

def GetreportIncidentEvent(start_timestamp, end_timestamp):
    try:
        start_datetime = parse_date(start_timestamp)
        end_datetime = parse_date(end_timestamp)

        session = Session()
        events = session.query(IncidentEvent).filter(
            IncidentEvent.date_created >= start_datetime,
            IncidentEvent.date_created <= end_datetime
        ).all()
        events_list = [event.to_dict() for event in events]
        return events_list, 200
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        return {"error": "Invalid date format provided."}, 400
    except SQLAlchemyError as e:
        logger.error(f"Database query error for IncidentEvent: {e}")
        return {"error": "An error occurred while fetching incident events."}, 500
    except Exception as e:
        logger.error(f"Unexpected error for IncidentEvent: {e}")
        return {"error": "An unexpected error occurred."}, 500
    finally:
        session.close()

# [V4] \/
def process_messages():
    """Process event messages from Kafka, excluding datetime from the payload."""
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', reset_offset_on_start=False, auto_offset_reset=OffsetType.LATEST)

    logger.info("Kafka consumer has started.")

    for message in consumer:
        if message is not None:
            
            msg_str = message.value.decode('utf-8')
            msg = json.loads(msg_str)
            
            logger.info(f"Consumed message: {msg}")
            logger.debug(f"Message received: {msg_str}")
            
            payload = msg.get('payload', {})
            payload.pop('datetime', None)
            
            if "type" in msg:
                if msg["type"] == "VehicleStatusEvent":
                    reportVehicleStatusEvent(msg['payload'])
                elif msg["type"] == "IncidentEvent":
                    reportIncidentEvent(msg['payload'])
            else:
                logger.info(f"Received non-event message: {msg}")
            consumer.commit_offsets()

def get_kafka_producer():
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    
    topic = client.topics[str.encode(app_config['kafka']['event_log_topic'])]
    log_topic = client.topics[str.encode(app_config['kafka']['event_log_topic'])]
    
    producer = client.get_sync_producer()
    log_producer = log_topic.get_sync_producer()

    producer = topic.get_sync_producer()
    message = {
        'service': 'storage',
        'message': 'Storage is ready to consume messages',
        'code': '0002'
    }
    
    log_producer.produce(json.dumps(message).encode('utf-8'))
    
    logger.info("Initialization message sent to Kafka.")

    return producer

def send_initialization_message(producer):
    message = {
        'service': 'storage', 
        'message': 'Storage is ready to consume messages', 
        'code': '0002'
    }
    producer.produce(json.dumps(message).encode('utf-8'))
    logger.info("Initialization message sent to Kafka.")
    pass

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('Transit.yaml', base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info("Starting Data Storage Service.")
    # producer = get_kafka_producer()  # Initialize the Kafka producer
    # send_initialization_message(producer)  # Send the initialization message
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    logger.info("Data Storage Service successfully started. Now running Flask app.")
    app.run(host='0.0.0.0', port=8090)
