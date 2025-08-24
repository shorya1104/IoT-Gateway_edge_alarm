#!/usr/bin/env python3

import signal
import sys
import time
import yaml
import threading
from datetime import datetime


from src.services.mqtt_service import MQTTService
from src.services.alarm_processor import AlarmProcessor
from src.services.storage_service import StorageService
from src.utils.logger import setup_logger, get_logger


class AlarmService:
    """Main alarm service application"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # Setup logging first
        self.logger = setup_logger(config_path)
        self.logger.info("Starting IoT Gateway Alarm Service")
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize services
        self.storage_service = None
        self.mqtt_service = None
        self.alarm_processor = None
        
        # Service state
        self._running = False
        self._shutdown_event = threading.Event()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_event.set()
    
    def _initialize_services(self):
        """Initialize all service components"""
        try:
            # Initialize storage service
            db_path = self.config['database']['path']
            self.storage_service = StorageService(db_path)
            self.logger.info("Storage service initialized")
            
            # Initialize MQTT service
            mqtt_config = self.config['mqtt']
            self.mqtt_service = MQTTService(
                broker=mqtt_config['broker'],
                port=mqtt_config['port'],
                username=mqtt_config.get('username'),
                password=mqtt_config.get('password'),
                client_id=mqtt_config['client_id']
            )
            self.logger.info("MQTT service initialized")
            
            # Initialize alarm processor
            processing_config = self.config['processing']
            self.alarm_processor = AlarmProcessor(
                storage_service=self.storage_service,
                max_workers=processing_config['max_workers']
            )
            self.logger.info("Alarm processor initialized")
            
            # Setup service connections
            self.mqtt_service.set_data_callback(self.alarm_processor.process_sensor_data)
            self.alarm_processor.set_alarm_callback(self._handle_alarm_notification)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    def _handle_alarm_notification(self, alarm_data: dict):
        """Handle alarm notifications and publish to MQTT"""
        try:
            # Log the alarm
            self.logger.warning(f"ALARM TRIGGERED: {alarm_data['rule_id']} - {alarm_data['description']}")
            
            # Publish alarm to MQTT
            if self.mqtt_service and self.mqtt_service.is_connected():
                alarm_topic = self.config['mqtt']['alarm_topic']
                self.mqtt_service.publish_alarm(alarm_data, alarm_topic)
            
        except Exception as e:
            self.logger.error(f"Error handling alarm notification: {e}")
    
    def _start_services(self):
        """Start all services"""
        try:
            # Start alarm processor
            self.alarm_processor.start()
            
            # Connect to MQTT and start processing
            if not self.mqtt_service.connect():
                raise Exception("Failed to connect to MQTT broker")
            
            # Subscribe to sensor topics
            subscribe_topic = self.config['mqtt']['subscribe_topic']
            if not self.mqtt_service.subscribe_to_sensors(subscribe_topic):
                raise Exception("Failed to subscribe to sensor topics")
            
            # Start MQTT message processing
            processing_config = self.config['processing']
            self.mqtt_service.start_processing(processing_config['max_workers'])
            
            self.logger.info("All services started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            raise
    
    def _stop_services(self):
        """Stop all services gracefully"""
        try:
            self.logger.info("Stopping services...")
            
            if self.mqtt_service:
                self.mqtt_service.disconnect()
                self.logger.info("MQTT service stopped")
            
            if self.alarm_processor:
                self.alarm_processor.stop()
                self.logger.info("Alarm processor stopped")
            
            # Cleanup old alarm history
            if self.storage_service:
                retention_days = self.config['alarm_defaults']['retention_days']
                self.storage_service.cleanup_old_history(retention_days)
                self.logger.info("Storage cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
    
    def _print_status(self):
        """Print service status information"""
        try:
            device_count = self.alarm_processor.get_device_count()
            active_alarms = len(self.alarm_processor.get_active_alarms())
            
            self.logger.info(f"Service Status - Devices: {device_count}, Active Alarms: {active_alarms}")
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
    
    def run(self):
        """Main service run loop"""
        try:
            self.logger.info("Initializing IoT Gateway Alarm Service...")
            
            # Initialize and start services
            self._initialize_services()
            self._start_services()
            
            self._running = True
            self.logger.info("IoT Gateway Alarm Service is running. Press Ctrl+C to stop.")
            
            # Main service loop
            status_interval = self.config['processing']['check_interval']
            last_status_time = time.time()
            
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Wait for shutdown signal
                    if self._shutdown_event.wait(timeout=1.0):
                        break
                    
                    # Print status periodically
                    current_time = time.time()
                    if current_time - last_status_time >= status_interval:
                        self._print_status()
                        last_status_time = current_time
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Critical error in alarm service: {e}")
            return 1
        
        finally:
            self._running = False
            self._stop_services()
            self.logger.info("IoT Gateway Alarm Service stopped")
        
        return 0

def main():
    """Application entry point"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="IoT Gateway Alarm Service")
    parser.add_argument('--config', '-c', 
                       default='config/config.yaml',
                       help='Configuration file path (default: config/config.yaml)')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='Run as daemon process')
    
    args = parser.parse_args()
    
    # Validate config file exists
    if not os.path.exists(args.config):
        print(f"Configuration file not found: {args.config}")
        return 1
    
    # Create and run service
    try:
        service = AlarmService(args.config)
        return service.run()
        
    except Exception as e:
        print(f"Failed to start alarm service: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())