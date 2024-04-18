from sqlalchemy import Column, Integer, String, DateTime
from base import Base
from datetime import datetime
import uuid

# [V2] added trace_id
class IncidentEvent(Base):
    __tablename__ = 'incident_events'
    id = Column(Integer, primary_key=True)  # Auto-incrementing ID
    uuid = Column(String, default=lambda: str(uuid.uuid4()))
    incidentType = Column(String)
    incidentSeverity = Column(Integer)
    expectedDuration = Column(String)
    userId = Column(String)
    trace_id = Column(String)  # Ensure this line is added correctly
    date_created = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert instance to dictionary."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'incidentType': self.incidentType,
            'incidentSeverity': self.incidentSeverity,
            'expectedDuration': self.expectedDuration,
            'userId': self.userId,
            'trace_id': self.trace_id,
            'date_created': self.date_created.isoformat() if self.date_created else None
        }