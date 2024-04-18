import mysql.connector
from mysql.connector import Error
import yaml

def create_tables():
    try:
        # Load configuration from YAML file
        with open('app_conf.yaml', 'r') as f:
            config = yaml.safe_load(f)

        connection=None
        connection = mysql.connector.connect(
            host=config['datastore']['hostname'],
            user=config['datastore']['user'],
            password=config['datastore']['password'],
            database=config['datastore']['db']
        )
        print(connection)

        cursor = connection.cursor()
        vehicle_status_events_table = """
        CREATE TABLE IF NOT EXISTS vehicle_status_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL,
            distanceTravelled INT,
            timeToArrival VARCHAR(50),
            onTimeScore INT,
            userId VARCHAR(36),
            trace_id VARCHAR(36),
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        incident_events_table = """
        CREATE TABLE IF NOT EXISTS incident_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL,
            incidentType VARCHAR(250) NOT NULL,
            incidentSeverity INT NOT NULL,
            expectedDuration VARCHAR(50) NOT NULL,
            userId VARCHAR(36) NOT NULL,
            trace_id VARCHAR(36) NOT NULL,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(vehicle_status_events_table)
        cursor.execute(incident_events_table)
        print("Tables created successfully.")
    except Error as e:
        print(f"Error creating tables: {e}")
    finally:
        print("Done with Tables")
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    # Pass the path to the configuration file
    create_tables()
