from threading import Thread
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from pykafka import KafkaClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from anomoly import Anomaly
import json
from base import Base
import datetime
import yaml
import logging
import logging.config
import os
import connexion
from flask_cors import CORS
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from flask import Flask
from pykafka.common import OffsetType


environment = os.getenv("TARGET_ENV", "development")

# Define configuration paths based on the environment
config_path = "/config/" if environment == "test" else "./"
app_conf_file = f"{config_path}app_conf.yaml"
log_conf_file = f"{config_path}log_conf.yaml"

# Load application configuration
try:
    with open(app_conf_file, 'r') as f:
        app_config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"Error: Configuration file not found at {app_conf_file}")
    exit(1)

# Load and configure logging
try:
    with open(log_conf_file, 'r') as f:
        log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)
except Exception as e:
    print(f"Error loading logging configuration: {e}")
    exit(1)
logger = logging.getLogger('basicLogger')

# Create the anomaly table if it doesn't exist
engine = create_engine('sqlite:///anomaly.sqlite')

try:
    database_uri = f"sqlite:////{app_config['datastore']['filename']}"
    print(f"\n{database_uri}\n")
    engine = create_engine(database_uri, echo=True)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    logger.info("Database connected successfully.")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    exit(1)

logger.info(f"Application started in {environment} environment.")  
logger.info(f"Thresshold values: {app_config['anomaly']['thress1']}, {app_config['anomaly']['thress2']}")
# [V4] KAFKA
# logger.info(f"Connecting to MySQL database at {app_config['datastore']['hostname']}:{app_config['datastore']['port']}")
# try:
#     DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
#     Session = sessionmaker(bind=DB_ENGINE)
#     logger.info("Database engine and sessionmaker successfully created.")
# except Exception as e:
#     logger.error(f"Failed to create database engine or sessionmaker: {e}")

# Create Kafka Consumer
def create_kafka_consumer():
    client = KafkaClient(hosts=app_config['kafka']['hosts'])
    topic = client.topics[app_config['kafka']['topic'].encode('utf-8')]
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', reset_offset_on_start=False, auto_offset_reset=OffsetType.LATEST)
    return consumer

def consume_messages():
    """Consumes messages from Kafka and logs them to sqlite."""
    consumer = create_kafka_consumer()
    for message in consumer:
        if message is not None:
            msg_str = message.value.decode('utf-8')
            msg = json.loads(msg_str)
            
            # logger.debug(f"Message received: {msg_str}")
            
            payload = msg.get('payload', {})
            payload.pop('datetime', None)

            if "type" in msg:
                if msg["type"] == "VehicleStatusEvent":
                    if (msg['payload']['distanceTravelled']) > app_config['anomaly']['thress1']:
                        logger.info(f"Anomaly detected: {msg['type'], msg['payload']['distanceTravelled'], app_config['anomaly']['thress1']}")

                elif msg["type"] == "IncidentEvent":
                    print(f"IncidentEvent{msg['payload']['incidentSeverity']}")
                    if (msg['payload']['incidentSeverity']) > app_config['anomaly']['thress2']:
                        logger.info(f"Anomaly detected: {msg['type'], msg['payload']['incidentSeverity'], app_config['anomaly']['thress2']}")
            else:
                logger.info(f"Received non-event message: {msg}")
            consumer.commit_offsets()

app = connexion.FlaskApp(__name__, specification_dir='./')

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.add_api('openapi1.yaml', base_path="/anomaly", strict_validation=True, validate_responses=True)

@app.route('/anomalies', methods=['GET'])
def get_anomalies():
    # Get the anomaly type from query parameters
    anomaly_type = request.args.get('type')

    # Query the anomalies from the database
    session = sessionmaker(bind=engine)()
    anomalies = session.query(Anomaly).filter_by(anomaly_type=anomaly_type).order_by(Anomaly.date_created.desc()).all()

    # Convert anomalies to dictionary representation
    anomalies_dict = [anomaly.to_dict() for anomaly in anomalies]

    return json.dumps(anomalies_dict)


if __name__ == '__main__':
    t1 = Thread(target=consume_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(host='0.0.0.0', port=8200)