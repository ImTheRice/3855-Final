import mysql.connector
from mysql.connector import Error

def drop_tables():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='acit3855group4kafka.eastus2.cloudapp.azure.com',
            user='superbaddefault',  
            password='superbaddefault',  
            database='events'
        )
        cursor = connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS vehicle_status_events")
        cursor.execute("DROP TABLE IF EXISTS incident_events")
        print("`vehicle_status_events` and `incident_events` tables dropped successfully.")
    except Error as e:
        print(f"Error dropping tables: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    drop_tables()
