import argparse
import yaml
from datetime import datetime
from typing import List
import os
import sys


# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.alarm_rule import AlarmRule, AlarmType, ComparisonOperator
from src.services.storage_service import StorageService
from src.utils.logger import get_logger

class AlarmCLI:
    """Command-line interface for alarm rule management"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.logger = get_logger('AlarmCLI')
        
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Initialize storage service
            db_path = self.config['database']['path']
            self.storage = StorageService(db_path)
            
        except Exception as e:
            print(f"Error initializing CLI: {e}")
            sys.exit(1)
    
    def add_simple_alarm(self, rule_id: str, device_id: str, sensor_field: str,
                        operator: str, threshold: float, duration: int, description: str):
        """Add a simple threshold alarm rule"""
        try:
            # Parse operator
            op = ComparisonOperator(operator)
            
            # Create alarm rule
            rule = AlarmRule(
                rule_id=rule_id,
                device_id=device_id,
                alarm_type=AlarmType.SIMPLE_THRESHOLD,
                sensor_field=sensor_field,
                threshold_value=threshold,
                comparison_operator=op,
                duration_minutes=duration,
                description=description,
                created_at=datetime.now().isoformat()
            )
            
            # Validate rule
            if not rule.validate():
                print("Error: Invalid alarm rule configuration")
                return False
            
            # Save rule
            if self.storage.save_alarm_rule(rule):
                print(f"Successfully added alarm rule: {rule_id}")
                return True
            else:
                print(f"Failed to save alarm rule: {rule_id}")
                return False
                
        except Exception as e:
            print(f"Error adding alarm rule: {e}")
            return False
    
    def add_conditional_alarm(self, rule_id: str, device_id: str, sensor_field: str,
                            operator: str, threshold: float, duration: int,
                            shunt_device: str, shunt_field: str, shunt_operator: str,
                            shunt_threshold: float, description: str):
        """Add a conditional threshold alarm rule"""
        try:
            # Parse operators
            op = ComparisonOperator(operator)
            shunt_op = ComparisonOperator(shunt_operator)
            
            # Create alarm rule
            rule = AlarmRule(
                rule_id=rule_id,
                device_id=device_id,
                alarm_type=AlarmType.CONDITIONAL_THRESHOLD,
                sensor_field=sensor_field,
                threshold_value=threshold,
                comparison_operator=op,
                duration_minutes=duration,
                description=description,
                shunt_device_id=shunt_device,
                shunt_field=shunt_field,
                shunt_value=shunt_threshold,
                shunt_operator=shunt_op,
                created_at=datetime.now().isoformat()
            )
            
            # Validate rule
            if not rule.validate():
                print("Error: Invalid alarm rule configuration")
                return False
            
            # Save rule
            if self.storage.save_alarm_rule(rule):
                print(f"Successfully added conditional alarm rule: {rule_id}")
                return True
            else:
                print(f"Failed to save alarm rule: {rule_id}")
                return False
                
        except Exception as e:
            print(f"Error adding conditional alarm rule: {e}")
            return False
    
    def list_alarm_rules(self, device_id: str = None):
        """List all alarm rules or rules for specific device"""
        try:
            rules = self.storage.get_all_alarm_rules(device_id)
            
            if not rules:
                print("No alarm rules found")
                return
            
            print(f"\n{'Rule ID':<20} {'Device ID':<15} {'Type':<20} {'Field':<12} {'Operator':<10} {'Threshold':<10} {'Duration':<10} {'Enabled':<8}")
            print("-" * 120)
            
            for rule in rules:
                print(f"{rule.rule_id:<20} {rule.device_id:<15} {rule.alarm_type.value:<20} "
                     f"{rule.sensor_field:<12} {rule.comparison_operator.value:<10} "
                     f"{rule.threshold_value:<10} {rule.duration_minutes:<1} {rule.enabled}")
                
                if rule.is_conditional():
                    print(f"{'└─ Shunt:':<20} {rule.shunt_device_id:<15} {'':<20} "
                         f"{rule.shunt_field:<12} {rule.shunt_operator.value:<10} "
                         f"{rule.shunt_value:<10}")
                print()
            
        except Exception as e:
            print(f"Error listing alarm rules: {e}")
    
    def delete_alarm_rule(self, rule_id: str):
        """Delete an alarm rule"""
        try:
            if self.storage.delete_alarm_rule(rule_id):
                print(f"Successfully deleted alarm rule: {rule_id}")
                return True
            else:
                print(f"Failed to delete alarm rule: {rule_id}")
                return False
                
        except Exception as e:
            print(f"Error deleting alarm rule: {e}")
            return False
    
    def show_alarm_rule(self, rule_id: str):
        """Show detailed information about an alarm rule"""
        try:
            rule = self.storage.get_alarm_rule(rule_id)
            if not rule:
                print(f"Alarm rule not found: {rule_id}")
                return
            
            print(f"\nAlarm Rule Details:")
            print(f"  Rule ID: {rule.rule_id}")
            print(f"  Device ID: {rule.device_id}")
            print(f"  Type: {rule.alarm_type.value}")
            print(f"  Description: {rule.description}")
            print(f"  Sensor Field: {rule.sensor_field}")
            print(f"  Threshold: {rule.comparison_operator.value} {rule.threshold_value}")
            print(f"  Duration: {rule.duration_minutes} minutes")
            print(f"  Enabled: {rule.enabled}")
            print(f"  Created: {rule.created_at}")
            
            if rule.is_conditional():
                print(f"\n  Shunt Condition:")
                print(f"    Device: {rule.shunt_device_id}")
                print(f"    Field: {rule.shunt_field}")
                print(f"    Condition: {rule.shunt_operator.value} {rule.shunt_value}")
            
            print()
            
        except Exception as e:
            print(f"Error showing alarm rule: {e}")
    
    def show_active_alarms(self):
        """Show currently active alarms"""
        try:
            states = self.storage.get_all_alarm_states()
            active_states = [state for state in states if state.is_violation_active()]
            
            if not active_states:
                print("No active alarms")
                return
            
            print(f"\n{'Rule ID':<20} {'Device ID':<15} {'Status':<12} {'Duration':<12} {'Last Value':<12}")
            print("-" * 80)
            
            current_time = datetime.now().timestamp()
            for state in active_states:
                duration = state.get_violation_duration_minutes(current_time)
                print(f"{state.rule_id:<20} {state.device_id:<15} {state.status.value:<12} "
                     f"{duration:.1f} min{'':<2} {state.last_value or 'N/A':<12}")
            
            print()
            
        except Exception as e:
            print(f"Error showing active alarms: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="IoT Gateway Alarm Rule Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add simple alarm
    add_simple = subparsers.add_parser('add-simple', help='Add simple threshold alarm')
    add_simple.add_argument('rule_id', help='Unique rule identifier')
    add_simple.add_argument('device_id', help='Device identifier')
    add_simple.add_argument('sensor_field', help='Sensor field name (e.g., temperature)')
    add_simple.add_argument('operator', choices=['>', '<', '>=', '<=', '==', '!='], 
                           help='Comparison operator')
    add_simple.add_argument('threshold', type=float, help='Threshold value')
    add_simple.add_argument('duration', type=int, help='Duration in minutes')
    add_simple.add_argument('description', help='Alarm description')
    
    # Add conditional alarm
    add_conditional = subparsers.add_parser('add-conditional', help='Add conditional threshold alarm')
    add_conditional.add_argument('rule_id', help='Unique rule identifier')
    add_conditional.add_argument('device_id', help='Device identifier')
    add_conditional.add_argument('sensor_field', help='Sensor field name')
    add_conditional.add_argument('operator', choices=['>', '<', '>=', '<=', '==', '!='])
    add_conditional.add_argument('threshold', type=float, help='Threshold value')
    add_conditional.add_argument('duration', type=int, help='Duration in minutes')
    add_conditional.add_argument('shunt_device', help='Shunt condition device ID')
    add_conditional.add_argument('shunt_field', help='Shunt condition field')
    add_conditional.add_argument('shunt_operator', choices=['>', '<', '>=', '<=', '==', '!='])
    add_conditional.add_argument('shunt_threshold', type=float, help='Shunt threshold')
    add_conditional.add_argument('description', help='Alarm description')
    
    # List rules
    list_rules = subparsers.add_parser('list', help='List alarm rules')
    list_rules.add_argument('--device', help='Filter by device ID')
    
    # Delete rule
    delete_rule = subparsers.add_parser('delete', help='Delete alarm rule')
    delete_rule.add_argument('rule_id', help='Rule ID to delete')
    
    # Show rule
    show_rule = subparsers.add_parser('show', help='Show alarm rule details')
    show_rule.add_argument('rule_id', help='Rule ID to show')
    
    # Show active alarms
    subparsers.add_parser('active', help='Show active alarms')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = AlarmCLI()
    
    # Execute command
    if args.command == 'add-simple':
        cli.add_simple_alarm(
            args.rule_id, args.device_id, args.sensor_field,
            args.operator, args.threshold, args.duration, args.description
        )
    
    elif args.command == 'add-conditional':
        cli.add_conditional_alarm(
            args.rule_id, args.device_id, args.sensor_field,
            args.operator, args.threshold, args.duration,
            args.shunt_device, args.shunt_field, args.shunt_operator,
            args.shunt_threshold, args.description
        )
    
    elif args.command == 'list':
        cli.list_alarm_rules(args.device)
    
    elif args.command == 'delete':
        cli.delete_alarm_rule(args.rule_id)
    
    elif args.command == 'show':
        cli.show_alarm_rule(args.rule_id)
    
    elif args.command == 'active':
        cli.show_active_alarms()

if __name__ == '__main__':
    main()