import os
import json
import yaml
import logging.config
from flask import Flask, jsonify, request
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
import connexion

app = Flask(__name__)

# Load configuration
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

# Create Kafka Consumer
def create_kafka_consumer():
    client = KafkaClient(hosts=app_config['kafka']['hosts'])
    topic = client.topics[app_config['kafka']['topic'].encode('utf-8')]
    consumer = topic.get_simple_consumer(
        auto_offset_reset=OffsetType.EARLIEST, 
        reset_offset_on_start=True
    )
    return consumer

consumer = create_kafka_consumer()

# Path to JSON database
json_db_path = app_config['database']['path']

def log_event_to_json(event_data):
    """Logs event to a JSON file as a dictionary."""
    try:
        os.makedirs(os.path.dirname(json_db_path), exist_ok=True)
        
        # Initialize file with an empty dictionary if it does not exist
        if not os.path.isfile(json_db_path) or os.stat(json_db_path).st_size == 0:
            with open(json_db_path, 'w') as file:
                json.dump({"0001": 0, "0002": 0, "0003": 0, "0004": 0}, file)
        
        # Read the existing data, update the event count, and write back to the file
        with open(json_db_path, 'r+') as file:
            events = json.load(file)
            code = event_data.get('code')
            events[code] = events.get(code, 0) + 1
            file.seek(0)
            file.truncate()
            json.dump(events, file, indent=4)

        logger.info(f"Event logged successfully: {event_data}")
    except Exception as e:
        logger.exception(f"Failed to log event to JSON: {e}")

def consume_messages():
    """Consumes messages from Kafka and logs them to JSON."""
    for message in consumer:
        if message is not None:
            try:
                event_data = json.loads(message.value.decode('utf-8'))
                # Log the event to JSON
                log_event_to_json(event_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

@app.route("/events_stats", methods=["GET"])
def fetch_event_stats():
    """Fetches and returns event counts by code from a JSON file."""
    try:
        with open(json_db_path, 'r') as file:
            events = json.load(file)
        return jsonify(events), 200
    except FileNotFoundError:
        logger.error("JSON file not found")
        return jsonify({"error": "JSON file not found"}), 404
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in the file: {e}")
        return jsonify({"error": "Invalid JSON in the file"}), 500
    except Exception as e:
        logger.error(f"Internal Server Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('transit.yaml', base_path="/event_logger", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    # Start the Kafka consumer thread
    thread = Thread(target=consume_messages)
    thread.setDaemon(True)
    thread.start()
    # Start the Flask app
    app.run(host='0.0.0.0', port=8120, debug=True)
