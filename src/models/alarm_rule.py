from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum
import json

class AlarmType(Enum):
    SIMPLE_THRESHOLD = "simple_threshold"
    CONDITIONAL_THRESHOLD = "conditional_threshold"

class ComparisonOperator(Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="

@dataclass
class  AlarmRule:
    """Data model for alarm rules"""
    rule_id: str
    device_id: str
    alarm_type: AlarmType
    sensor_field: str  # e.g., "temperature", "humidity"
    threshold_value: float
    comparison_operator: ComparisonOperator
    duration_minutes: int
    description: str
    enabled: bool = True
    
    # For conditional threshold alarms
    shunt_device_id: Optional[str] = None
    shunt_field: Optional[str] = None
    shunt_value: Optional[float] = None
    shunt_operator: Optional[ComparisonOperator] = None
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['alarm_type'] = self.alarm_type.value
        data['comparison_operator'] = self.comparison_operator.value
        if self.shunt_operator:
            data['shunt_operator'] = self.shunt_operator.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlarmRule':
        """Create AlarmRule from dictionary"""
        data['alarm_type'] = AlarmType(data['alarm_type'])
        data['comparison_operator'] = ComparisonOperator(data['comparison_operator'])
        if data.get('shunt_operator'):
            data['shunt_operator'] = ComparisonOperator(data['shunt_operator'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AlarmRule':
        """Create AlarmRule from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def is_conditional(self) -> bool:
        """Check if this is a conditional threshold alarm"""
        return self.alarm_type == AlarmType.CONDITIONAL_THRESHOLD
    
    def validate(self) -> bool:
        """Validate alarm rule configuration"""
        if not all([self.rule_id, self.device_id, self.sensor_field]):
            return False
        
        if self.duration_minutes <= 0:
            return False
        
        if self.is_conditional():
            if not all([self.shunt_device_id, self.shunt_field, 
                       self.shunt_value is not None, self.shunt_operator]):
                return False
        
        return True