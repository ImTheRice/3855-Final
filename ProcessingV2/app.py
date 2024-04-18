# Standard library imports
import datetime
import json
import logging
import logging.config

# Related third-party imports
import colorlog
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify
from pykafka import KafkaClient
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uvicorn
import yaml

# Local application/library-specific imports
import connexion
from base import Base
from stats import Stats

from flask_cors import CORS
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import os
from apscheduler.triggers.interval import IntervalTrigger

# Determine the current environment
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

# Setup the database connection
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

def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        populate_stats,
        trigger=IntervalTrigger(seconds=app_config['scheduler']['period_sec']),
        next_run_time=datetime.datetime.now()  # This schedules it to run as soon as the scheduler starts
    )

    scheduler.start()
    logger.info("Scheduler started and populate_stats scheduled to run immediately.")

def populate_stats():
    """
    This function is called periodically to update statistics based on new vehicle status
    and incident report events. It fetches new events since the last update, ensuring no duplicates,
    and updates the statistics, including counts and maximum values.
    """
    logger.info("Starting to populate stats")
    current_datetime = datetime.datetime.now(datetime.timezone.utc)
    producer = get_kafka_producer()

    with DBSession() as session:
        # Retrieve the most recent stats record, or initialize if none exist.
        last_stat = session.query(Stats).order_by(Stats.last_updated.desc()).first()
        if not last_stat:
            logger.info("No stats entries found. Initializing.")
            last_stat = Stats(
                num_vehicle_status_events=0,
                num_incident_events=0,
                max_distance_travelled=0,
                max_incident_severity=0,
                last_updated=current_datetime - datetime.timedelta(seconds=1)
            )
            session.add(last_stat)
            session.commit()
            last_stat = session.query(Stats).order_by(Stats.last_updated.desc()).first()

        # Calculate timestamps for API requests
        start_timestamp = (last_stat.last_updated + datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_timestamp = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.debug(f"Fetching events from {start_timestamp} to {end_timestamp}")

        # Fetch Vehicle Status Events
        vehicle_url = f"{app_config['eventstore']['url']}/events/vehicle-status"
        response = requests.get(vehicle_url, params={'start_timestamp': start_timestamp, 'end_timestamp': end_timestamp})
        vehicle_events = response.json() if response.status_code == 200 else []
        logger.info(f"Fetched {len(vehicle_events)} new vehicle events.")

        # Fetch Incident Report Events
        incident_url = f"{app_config['eventstore']['url']}/events/incident-report"
        response = requests.get(incident_url, params={'start_timestamp': start_timestamp, 'end_timestamp': end_timestamp})
        incident_events = response.json() if response.status_code == 200 else []
        logger.info(f"Fetched {len(incident_events)} new incident events.")

        total_events_processed = len(vehicle_events) + len(incident_events)

        if total_events_processed > 25:
            try:
                message = {
                    'service': 'processor',
                    'message': 'Processor handled more than 25 messages since the last run',
                    'code': '0004',
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
                producer.produce(json.dumps(message).encode('utf-8'))
                logger.info(f"Published message to Kafka: {message}")
            except Exception as e:
                logger.error(f"Failed to publish message to Kafka: {e}") 


        # Update statistics with fetched events
        if vehicle_events or incident_events:

            last_stat.num_vehicle_status_events += len(vehicle_events)
            last_stat.num_incident_events += len(incident_events)

            vehicle_distances = [event.get('distanceTravelled', 0) for event in vehicle_events]
            incident_severities = [event.get('incidentSeverity', 0) for event in incident_events]

            if vehicle_distances:
                last_stat.max_distance_travelled = max([last_stat.max_distance_travelled] + vehicle_distances)
            if incident_severities:
                last_stat.max_incident_severity = max([last_stat.max_incident_severity] + incident_severities)

            last_stat.last_updated = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%SZ")
            session.commit()
            logger.debug(f"Updated last_stat timestamp to {last_stat.last_updated}")

            if total_events_processed > 25:
                message = {
                    'service': 'processor',
                    'message': 'Processor handled more than 25 messages since the last run',
                    'code': '0004',
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
                producer.produce(json.dumps(message).encode('utf-8'))
                logger.info(f"Published message to Kafka: {message}")
        else:
            logger.info("No new events found. Skipping stats update.")

def get_stats():
    session = DBSession()
    latest_stat = session.query(Stats).order_by(Stats.last_updated.desc()).first()
    session.close()

    if not latest_stat:
        logger.error("Statistics do not exist")
        return jsonify({"error": "Statistics do not exist"}), 404
    
    try:
        stats_dict = latest_stat.to_dict()
        logger.debug(f"Stats returned: {stats_dict}")
        return jsonify(stats_dict), 200
    except Exception as e:
        logger.error(f"Error processing stats: {e}")
        return jsonify({"error": "Error processing statistics"}), 500

# Flask app setup
app = connexion.FlaskApp(__name__, specification_dir='')
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    app.add_middleware(CORSMiddleware, position=MiddlewarePosition.BEFORE_EXCEPTION, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_api('./Transit.yaml', base_path="/processing", strict_validation=True, validate_responses=True)
CORS(app.app)

# def get_kafka_producer():
#     client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
#     topic = client.topics[str.encode(app_config['kafka']['event_log_topic'])]
#     # log_topic = client.topics[str.encode(app_config['kafka']['event_log_topic'])]
#     producer = client.get_sync_producer()
#     # log_producer = log_topic.get_sync_producer()

#     return producer
def get_kafka_producer():
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['kafka']['event_log_topic'])]
    producer = topic.get_sync_producer()
    return producer

def send_initialization_message():
    producer = get_kafka_producer()
    message = {
        'service': 'process',
        'message': 'Processing is ready to consume messages',
        'code': '0003'
    }
    producer.produce(json.dumps(message).encode('utf-8'))
    logger.info("Initialization message sent to Kafka.")
if __name__ == '__main__':
    send_initialization_message()  # Send the initialization message
    Base.metadata.create_all(engine)
    init_scheduler()
    # producer = get_kafka_producer()  # Initialize the Kafka producer
    uvicorn.run(app="app:app", host="0.0.0.0", port=8100)
