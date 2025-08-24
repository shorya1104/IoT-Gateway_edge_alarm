import threading
import time
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from queue import Queue

from src.models.alarm_rule import AlarmRule, ComparisonOperator
from src.models.alarm_state import AlarmState, AlarmStatus
from src.services.storage_service import StorageService
from src.utils.logger import get_logger

class AlarmProcessor:
    """Core alarm processing service with parallel execution support"""
    
    def __init__(self, storage_service: StorageService, max_workers: int = 20):
        self.storage = storage_service
        self.max_workers = max_workers
        self.logger = get_logger('AlarmProcessor')
        
        # Thread-safe data structures
        self._device_data: Dict[str, Dict[str, Any]] = {}
        self._data_lock = threading.RLock()
        
        # Processing queue and thread pool
        self._processing_queue = Queue(maxsize=500)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AlarmProc")
        
        # Alarm callback
        self.alarm_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Background processing
        self._running = False
        self._processor_thread = None
        
        # Load existing states on startup
        self._load_alarm_states()
    
    def set_alarm_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for alarm notifications"""
        self.alarm_callback = callback
    
    def _load_alarm_states(self):
        """Load existing alarm states from storage"""
        try:
            states = self.storage.get_all_alarm_states()
            self.logger.info(f"Loaded {len(states)} existing alarm states")
        except Exception as e:
            self.logger.error(f"Failed to load alarm states: {e}")
    
    def process_sensor_data(self, device_id: str, data: Dict[str, Any]):
        """Process incoming sensor data (thread-safe)"""
        try:
            # Update device data cache
            with self._data_lock:
                self._device_data[device_id] = {
                    **data,
                    'last_update': datetime.now().timestamp()
                }
            
            # Add to processing queue
            if not self._processing_queue.full():
                self._processing_queue.put((device_id, data))
            else:
                self.logger.warning(f"Processing queue full, dropping data for device {device_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing sensor data for device {device_id}: {e}")
    
    def _process_device_alarms(self, device_id: str, data: Dict[str, Any]):
        """Process alarms for a specific device"""
        try:
            # Get all alarm rules for this device
            rules = self.storage.get_all_alarm_rules(device_id)
            
            for rule in rules:
                if not rule.enabled:
                    continue
                
                try:
                    self._evaluate_alarm_rule(rule, data)
                except Exception as e:
                    self.logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error processing alarms for device {device_id}: {e}")
    
    def _evaluate_alarm_rule(self, rule: AlarmRule, data: Dict[str, Any]):
        """Evaluate a single alarm rule against sensor data"""
        try:
            current_time = datetime.now().timestamp()
            
            # Get current alarm state
            state = self.storage.get_alarm_state(rule.rule_id)
            if state is None:
                state = AlarmState(
                    rule_id=rule.rule_id,
                    device_id=rule.device_id,
                    status=AlarmStatus.INACTIVE
                )
            
            # Get sensor value
            sensor_value = data.get(rule.sensor_field)
            if sensor_value is None:
                self.logger.debug(f"Sensor field {rule.sensor_field} not found in data for rule {rule.rule_id}")
                return
            
            # Evaluate primary condition
            primary_violated = self._evaluate_condition(
                sensor_value, rule.threshold_value, rule.comparison_operator
            )
            
            # Evaluate shunt condition for conditional alarms
            shunt_satisfied = True
            shunt_value = None
            
            if rule.is_conditional():
                shunt_satisfied, shunt_value = self._evaluate_shunt_condition(rule)
            
            # Combined condition
            condition_violated = primary_violated and shunt_satisfied
            
            if condition_violated:
                # Start or continue violation
                if not state.is_violation_active():
                    state.start_violation(current_time, sensor_value, shunt_value)
                    self.logger.info(f"Violation started for rule {rule.rule_id}")
                else:
                    # Update violation
                    state.last_violation = current_time
                    state.last_value = sensor_value
                    if shunt_value is not None:
                        state.last_shunt_value = shunt_value
                
                # Check if duration threshold is met
                violation_duration = state.get_violation_duration_minutes(current_time)
                
                if (violation_duration >= rule.duration_minutes and 
                    state.status != AlarmStatus.TRIGGERED):
                    
                    # Trigger alarm
                    state.trigger_alarm(current_time)
                    self._publish_alarm(rule, state, sensor_value, shunt_value)
                    
                    # Save to history
                    alarm_data = self._create_alarm_data(rule, state, sensor_value, shunt_value)
                    self.storage.save_alarm_history(rule.rule_id, rule.device_id, alarm_data)
                    
                    self.logger.info(f"Alarm triggered for rule {rule.rule_id} after {violation_duration:.1f} minutes")
            
            else:
                # No violation - clear if previously active
                if state.is_violation_active():
                    state.clear_violation()
                    self.logger.info(f"Violation cleared for rule {rule.rule_id}")
            
            # Save updated state
            self.storage.save_alarm_state(state)
            
        except Exception as e:
            self.logger.error(f"Error evaluating alarm rule {rule.rule_id}: {e}")
    
    def _evaluate_condition(self, value: float, threshold: float, operator: ComparisonOperator) -> bool:
        """Evaluate a condition based on operator"""
        try:
            if operator == ComparisonOperator.GREATER_THAN:
                return value > threshold
            elif operator == ComparisonOperator.LESS_THAN:
                return value < threshold
            elif operator == ComparisonOperator.GREATER_EQUAL:
                return value >= threshold
            elif operator == ComparisonOperator.LESS_EQUAL:
                return value <= threshold
            elif operator == ComparisonOperator.EQUAL:
                return abs(value - threshold) < 1e-6  # Float equality
            elif operator == ComparisonOperator.NOT_EQUAL:
                return abs(value - threshold) >= 1e-6
            else:
                self.logger.error(f"Unknown comparison operator: {operator}")
                return False
        except Exception as e:
            self.logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _evaluate_shunt_condition(self, rule: AlarmRule) -> tuple[bool, Optional[float]]:
        """Evaluate shunt condition for conditional alarms"""
        try:
            # Get shunt device data
            with self._data_lock:
                shunt_data = self._device_data.get(rule.shunt_device_id)
            
            if shunt_data is None:
                self.logger.debug(f"Shunt device {rule.shunt_device_id} data not available")
                return False, None
            
            shunt_value = shunt_data.get(rule.shunt_field)
            if shunt_value is None:
                self.logger.debug(f"Shunt field {rule.shunt_field} not found in data")
                return False, None
            
            condition_met = self._evaluate_condition(
                shunt_value, rule.shunt_value, rule.shunt_operator
            )
            
            return condition_met, shunt_value
            
        except Exception as e:
            self.logger.error(f"Error evaluating shunt condition: {e}")
            return False, None
    
    def _create_alarm_data(self, rule: AlarmRule, state: AlarmState, 
                          sensor_value: float, shunt_value: Optional[float] = None) -> Dict[str, Any]:
        """Create alarm data dictionary for notification"""
        alarm_data = {
            'rule_id': rule.rule_id,
            'device_id': rule.device_id,
            'alarm_type': rule.alarm_type.value,
            'description': rule.description,
            'sensor_field': rule.sensor_field,
            'current_value': sensor_value,
            'threshold_value': rule.threshold_value,
            'comparison_operator': rule.comparison_operator.value,
            'duration_minutes': rule.duration_minutes,
            'violation_duration': state.get_violation_duration_minutes(datetime.now().timestamp()),
            'trigger_time': state.trigger_time,
            'timestamp': datetime.now().isoformat(),
            'severity': 'HIGH'  # Could be made configurable
        }
        
        # Add conditional alarm information
        if rule.is_conditional() and shunt_value is not None:
            alarm_data.update({
                'shunt_device_id': rule.shunt_device_id,
                'shunt_field': rule.shunt_field,
                'shunt_value': shunt_value,
                'shunt_threshold': rule.shunt_value,
                'shunt_operator': rule.shunt_operator.value
            })
        
        return alarm_data
    
    def _publish_alarm(self, rule: AlarmRule, state: AlarmState, 
                      sensor_value: float, shunt_value: Optional[float] = None):
        """Publish alarm notification"""
        try:
            if self.alarm_callback:
                alarm_data = self._create_alarm_data(rule, state, sensor_value, shunt_value)
                self.alarm_callback(alarm_data)
        except Exception as e:
            self.logger.error(f"Error publishing alarm: {e}")
    
    def _background_processor(self):
        """Background thread for processing alarm queue"""
        while self._running:
            try:
                if not self._processing_queue.empty():
                    device_id, data = self._processing_queue.get(timeout=1)
                    
                    # Submit to thread pool for parallel processing
                    future = self._executor.submit(self._process_device_alarms, device_id, data)
                    
                    # Don't wait for completion - fire and forget for better throughput
                    self._processing_queue.task_done()
                
            except Exception as e:
                if self._running:
                    self.logger.error(f"Error in background processor: {e}")
    
    def start(self):
        """Start the alarm processor"""
        try:
            self._running = True
            self._processor_thread = threading.Thread(target=self._background_processor, name="AlarmProcessor")
            self._processor_thread.daemon = True
            self._processor_thread.start()
            
            self.logger.info(f"Alarm processor started with {self.max_workers} workers")
            
        except Exception as e:
            self.logger.error(f"Failed to start alarm processor: {e}")
            raise
    
    def stop(self):
        """Stop the alarm processor"""
        try:
            self._running = False
            
            if self._processor_thread:
                self._processor_thread.join(timeout=5)
            
            self._executor.shutdown(wait=True, timeout=10)
            
            self.logger.info("Alarm processor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping alarm processor: {e}")
    
    def get_device_count(self) -> int:
        """Get number of devices currently being monitored"""
        with self._data_lock:
            return len(self._device_data)
    
    def get_active_alarms(self) -> List[AlarmState]:
        """Get all currently active alarms"""
        try:
            all_states = self.storage.get_all_alarm_states()
            return [state for state in all_states if state.is_violation_active()]
        except Exception as e:
            self.logger.error(f"Error getting active alarms: {e}")
            return []