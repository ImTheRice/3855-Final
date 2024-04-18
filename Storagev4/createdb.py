import mysql.connector
from mysql.connector import Error
import yaml

def load_config(config_path='./app_conf.yaml'):
    with open(config_path, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    return cfg

def create_database():
    
    config = load_config()  # Load the configuration
    db_config = config['datastore']  # Access the datastore configuration

    try:
        connection=None
        connection = mysql.connector.connect(
         host=db_config['hostname'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS events")
        print("Database `events` created successfully.")

        cursor.execute("GRANT ALL PRIVILEGES ON events.* TO 'superbaddefault'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print("Granted all privileges to user 'superbaddefault' on database `events`.")

    except Error as e:
        print(f"Error creating database: {e}")
    finally:
        print("Done with CreateDB")
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    create_database()
