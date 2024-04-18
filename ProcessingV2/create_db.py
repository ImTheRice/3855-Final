import sqlite3

conn = sqlite3.connect('/data/stats.sqlite')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY,
    num_vehicle_status_events INTEGER NOT NULL DEFAULT 0,
    num_incident_events INTEGER NOT NULL DEFAULT 0,
    max_distance_travelled INTEGER,
    max_incident_severity INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

print("Database and tables created successfully.")
