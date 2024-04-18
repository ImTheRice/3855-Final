from sqlalchemy import Column, Integer, String, DateTime
from base import Base
from datetime import datetime
import uuid

# [V2] added trace_id
class VehicleStatusEvent(Base):
    __tablename__ = 'vehicle_status_events'
    id = Column(Integer, primary_key=True)  # Auto-incrementing ID
    uuid = Column(String, default=lambda: str(uuid.uuid4()))
    distanceTravelled = Column(Integer)
    timeToArrival = Column(String)
    onTimeScore = Column(Integer)
    userId = Column(String)
    trace_id = Column(String)  # Add this line for trace_id
    date_created = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert instance to dictionary."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'distanceTravelled': self.distanceTravelled,
            'timeToArrival': self.timeToArrival,
            'onTimeScore': self.onTimeScore,
            'userId': self.userId,
            'trace_id': self.trace_id,
            'date_created': self.date_created.isoformat() if self.date_created else None
        }