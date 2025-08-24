from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum
import json
from datetime import datetime

class AlarmStatus(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"

@dataclass
class AlarmState:
    """Data model for alarm state tracking"""
    rule_id: str
    device_id: str
    status: AlarmStatus
    violation_start: Optional[float] = None  # timestamp when violation started
    last_violation: Optional[float] = None   # last violation timestamp
    trigger_time: Optional[float] = None     # when alarm was triggered
    acknowledge_time: Optional[float] = None # when alarm was acknowledged
    violation_count: int = 0
    last_value: Optional[float] = None
    last_shunt_value: Optional[float] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().timestamp()
        self.updated_at = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlarmState':
        """Create AlarmState from dictionary"""
        data['status'] = AlarmStatus(data['status'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AlarmState':
        """Create AlarmState from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def start_violation(self, timestamp: float, value: float, shunt_value: Optional[float] = None):
        """Start tracking a violation"""
        if self.status == AlarmStatus.INACTIVE:
            self.violation_start = timestamp
            self.status = AlarmStatus.ACTIVE
        
        self.last_violation = timestamp
        self.violation_count += 1
        self.last_value = value
        if shunt_value is not None:
            self.last_shunt_value = shunt_value
        self.updated_at = datetime.now().timestamp()
    
    def clear_violation(self):
        """Clear the current violation"""
        self.status = AlarmStatus.INACTIVE
        self.violation_start = None
        self.last_violation = None
        self.violation_count = 0
        self.updated_at = datetime.now().timestamp()
    
    def trigger_alarm(self, timestamp: float):
        """Trigger the alarm"""
        self.status = AlarmStatus.TRIGGERED
        self.trigger_time = timestamp
        self.updated_at = datetime.now().timestamp()
    
    def acknowledge_alarm(self, timestamp: float):
        """Acknowledge the alarm"""
        self.status = AlarmStatus.ACKNOWLEDGED
        self.acknowledge_time = timestamp
        self.updated_at = datetime.now().timestamp()
    
    def get_violation_duration_minutes(self, current_timestamp: float) -> float:
        """Get violation duration in minutes"""
        if self.violation_start is None:
            return 0.0
        return (current_timestamp - self.violation_start) / 60.0
    
    def is_violation_active(self) -> bool:
        """Check if violation is currently active"""
        return self.status in [AlarmStatus.ACTIVE, AlarmStatus.TRIGGERED]