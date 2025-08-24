#!/usr/bin/env python3
"""
Setup sample alarm rules for testing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Add this at the very beginning, before any other imports


# Then change your imports to be absolute (remove the dots)
from src.services.storage_service import StorageService
# instead of: from .services.storage_service import StorageService
from datetime import datetime


# Add the src directory to the Python path
sys.path.append('src')

from src.models.alarm_rule import AlarmRule, AlarmType, ComparisonOperator
# from services.storage_service import StorageService
from src.services.storage_service import StorageService

def create_sample_rules():
    """Create sample alarm rules for testing"""
    
    # Initialize storage service
    storage = StorageService("data/alarms.db")
    
    # Sample rules to create
    rules = []
    
    # Simple threshold alarms for temperature
    for i in range(1, 100):  # devices 
        rule = AlarmRule(
            rule_id=f"temp_high_device_{i}",
            device_id=f"device-{i}",
            alarm_type=AlarmType.SIMPLE_THRESHOLD,
            sensor_field="temperature",
            threshold_value=30.0,
            comparison_operator=ComparisonOperator.GREATER_THAN,
            duration_minutes=2,  # 2 minutes for testing
            description=f"Temperature too high for device {i}",
            created_at=datetime.now().isoformat()
        )
        rules.append(rule)
    
    # Conditional alarms - temperature high AND device is on (current > 0)
    for i in range(1, 100):  # devices 
        rule = AlarmRule(
            rule_id=f"temp_conditional_device_{i}",
            device_id=f"device-{i}",
            alarm_type=AlarmType.CONDITIONAL_THRESHOLD,
            sensor_field="temperature",
            threshold_value=28.0,
            comparison_operator=ComparisonOperator.GREATER_THAN,
            duration_minutes=3,  # 3 minutes for testing
            description=f"Temperature high while device {i} is active",
            shunt_device_id=f"device-{i}",  # Same device for current reading
            shunt_field="current",
            shunt_value=0,
            shunt_operator=ComparisonOperator.GREATER_THAN,
            created_at=datetime.now().isoformat()
        )
        rules.append(rule)
    
    # Low temperature alarms for some devices
    for i in range(1, 100):  # devices 
        rule = AlarmRule(
            rule_id=f"temp_low_device_{i}",
            device_id=f"device-{i}",
            alarm_type=AlarmType.SIMPLE_THRESHOLD,
            sensor_field="temperature",
            threshold_value=22.0,
            comparison_operator=ComparisonOperator.LESS_THAN,
            duration_minutes=5,
            description=f"Temperature too low for device {i}",
            created_at=datetime.now().isoformat()
        )
        rules.append(rule)
    
    # Save all rules
    success_count = 0
    for rule in rules:
        if storage.save_alarm_rule(rule):
            success_count += 1
            print(f"Created rule: {rule.rule_id}")
        else:
            print(f"Failed to create rule: {rule.rule_id}")
    
    print(f"\nSuccessfully created {success_count}/{len(rules)} alarm rules")
    
    return success_count == len(rules)

if __name__ == "__main__":
    print("Creating sample alarm rules...")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    if create_sample_rules():
        print("Sample rules created successfully!")
        print("\nYou can now:")
        print("1. Run the alarm service: python src/main.py")
        print("2. Run the data simulator: python data_simulate.py")
        print("3. Use CLI to manage rules: python -m src.cli.alarm_cli list")
    else:
        print("Failed to create some sample rules")
        sys.exit(1)