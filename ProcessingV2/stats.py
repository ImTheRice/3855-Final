from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Stats(Base):
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True)
    num_vehicle_status_events = Column(Integer, nullable=False, default=0)
    num_incident_events = Column(Integer, nullable=False, default=0)
    max_distance_travelled = Column(Integer, nullable=True)
    max_incident_severity = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'num_vehicle_status_events': self.num_vehicle_status_events,
            'num_incident_events': self.num_incident_events,
            'max_distance_travelled': self.max_distance_travelled,
            'max_incident_severity': self.max_incident_severity,
            'last_updated': self.last_updated.isoformat()
        }
