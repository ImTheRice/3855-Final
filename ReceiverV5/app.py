import connexion
import yaml
import logging.config
import uuid
import colorlog
import json
from pykafka import KafkaClient
from pykafka.exceptions import KafkaException
import time
from connexion import NoContent

import os

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yaml"
    log_conf_file = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yaml"
    log_conf_file = "log_conf.yaml"

# Enhanced logger setup with colorlog for more intuitive debugging and log inspection
color_handler = colorlog.StreamHandler()
color_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s: %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

# Load externalized configurations for flexibility and easy maintenance
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
with open(log_conf_file, 'r') as f:
    logging.config.dictConfig(yaml.safe_load(f.read()))

# Set up the enhanced logger with color support
logger = logging.getLogger('basicLogger')
logger.addHandler(color_handler)

# Kafka connection setup with retry logic to ensure resilience on startup
# is_readiness_message_sent = False

def connect_to_kafka():
    max_retries = app_config['kafka']['max_retries']
    retry_delay = app_config['kafka']['retry_delay']
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to Kafka (Attempt {retry_count + 1}/{max_retries})")
            
            kafka_client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            kafka_topic = kafka_client.topics[str.encode(app_config['events']['topic'])]
            log_topic = kafka_client.topics[str.encode(app_config['kafka']['event_log_topic'])]
            producer = kafka_topic.get_sync_producer()
            log_producer = log_topic.get_sync_producer()

            readiness_message = {
                'service': 'receiver',
                'message': 'Receiver is ready to receive messages',
                'code': '0001'
            }
            log_producer.produce(json.dumps(readiness_message).encode('utf-8'))

            logger.info("Receiver Service successfully started. Ready to receive messages.")

            return kafka_client, kafka_topic
        
        except KafkaException as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            time.sleep(retry_delay)
            retry_count += 1
        except Exception as ex:
            logger.error(f"An unexpected error occurred: {ex}")
            time.sleep(retry_delay)
            retry_count += 1

    raise KafkaException("Maximum Kafka connection attempts exceeded")

# Initialize Kafka connection outside of request handling to improve performance
kafka_client, kafka_topic = connect_to_kafka()

# Producer setup is moved outside of the endpoint functions to improve performance
producer = kafka_topic.get_sync_producer()

def reportVehicleStatusEvent(body):
    """
    Produce Vehicle Status Event messages to Kafka.
    """
    if 'trace_id' not in body or not body['trace_id']:
        body['trace_id'] = str(uuid.uuid4())

    logger.info(f"Received Vehicle Status Event request with a trace id of {body['trace_id']}")

    message = {
        "type": "VehicleStatusEvent",
        "datetime": body.get("timestamp", ""),
        "payload": body
    }
    producer.produce(json.dumps(message).encode('utf-8'))

    logger.info(f"Produced Vehicle Status Event message with trace id {body['trace_id']}")

    return NoContent, 201

def reportIncidentEvent(body):
    """
    Produce Incident Event messages to Kafka.
    """
    if 'trace_id' not in body or not body['trace_id']:
        body['trace_id'] = str(uuid.uuid4())

    logger.info(f"Received Incident Event request with a trace id of {body['trace_id']}")

    message = {
        "type": "IncidentEvent",
        "datetime": body.get("timestamp", ""),
        "payload": body
    }

    producer.produce(json.dumps(message).encode('utf-8'))

    logger.info(f"Produced Incident Event message with trace id {body['trace_id']}")

    return NoContent, 201

# Placeholder functions for GET endpoints - presumably, implementations would follow similar patterns to POSTs
def GetreportVehicleStatusEvent():
    pass

def GetreportIncidentEvent():
    pass

# FlaskApp setup with API definition
app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('Transit.yaml', base_path="/receiver", strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    # Initialize Kafka connection outside of request handling to improve performance
    #kafka_client, kafka_topic = connect_to_kafka()
    #producer = kafka_topic.get_sync_producer()
    app.run(host='0.0.0.0', port=8080)

