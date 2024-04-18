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
# Base.metadata.create_all(engine)

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

# [V4] KAFKA
logger.info(f"Connecting to MySQL database at {app_config['datastore']['hostname']}:{app_config['datastore']['port']}")
try:
    DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
    Session = sessionmaker(bind=DB_ENGINE)
    logger.info("Database engine and sessionmaker successfully created.")
except Exception as e:
    logger.error(f"Failed to create database engine or sessionmaker: {e}")

logger.info(f"Application started in {environment} environment.")  
logger.info(f"Thresshold values: {app_config['anomaly']['thress1']}, {app_config['anomaly']['thress2']}")


# Create the Flask app object
app = Flask(__name__)


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

# @app.route('/events', methods=['POST'])
# def consume_event():
#     # Get the event data from the request
#     event_data = request.get_json()

#     logger.debug("Entering get_incident_event function")
#     try:
#         hostname = f'{app_config["events"]["hostname"]}:{app_config["events"]["port"]}'
#         client = KafkaClient(hosts=hostname)
#         topic = client.topics[str.encode(app_config["events"]["topic"])]
#         consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
#         logger.debug("Kafka consumer initialized")

#         count = 0
#         for msg in consumer:
#             if msg is not None and msg.value:
#                 msg_str = msg.value.decode('utf-8').strip()
#                 if msg_str:  # Check if msg_str is not empty
#                     try:
#                         msg = json.loads(msg_str)
#                         if msg["type"] == "IncidentEvent":
#                             if count == index:
#                                 logger.info(f"Incident Event found at index {index}")
#                                 return msg["payload"], 200
#                             count += 1
#                     except json.JSONDecodeError as e:
#                         logger.error(f"JSON decoding error: {e} - Message string: '{msg_str}'")
#                         continue  # Skip this message and continue with the next
#     except Exception as e:
#         logger.error(f"Error retrieving Incident Event: {e}", exc_info=True)
#     logger.error(f"Could not find Incident Event at index {index}")
    
    # return {"message": "Not Found"}, 404
    # If an anomaly is detected, create an Anomaly object and save it to the database
    # if is_anomaly:
    #     anomaly = Anomaly(event_id=event_data['event_id'],
    #                       trace_id=event_data['trace_id'],
    #                       event_type=event_data['event_type'],
    #                       anomaly_type='high' if is_high_anomaly else 'low',
    #                       description='Anomaly description',
    #                       date_created=datetime.datetime.now())
    #     db.session.add(anomaly)
    #     db.session.commit()

    # return 'Event consumed successfully'

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8200)