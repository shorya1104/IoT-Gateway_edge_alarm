import paho.mqtt.client as mqtt
import json
import threading
from queue import Queue
from typing import Callable, Dict, Any, Optional
from src.utils.logger import get_logger

class MQTTService:
    """MQTT service for handling device data and alarm notifications"""
    
    def __init__(self, broker: str, port: int, username: Optional[str] = None, 
                 password: Optional[str] = None, client_id: str = "alarm_service"):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.logger = get_logger('MQTTService')
        
        # Message queues for parallel processing
        self.message_queue = Queue(maxsize=1000)
        self.alarm_queue = Queue(maxsize=100)
        
        # MQTT client
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Callbacks
        self.data_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
        # Connection state
        self._connected = False
        self._lock = threading.Lock()
        
        # Worker threads
        self._workers = []
        self._running = False
    
    def set_data_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback function for processing incoming data"""
        self.data_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            with self._lock:
                self._connected = True
            self.logger.info(f"Connected to MQTT broker {self.broker}:{self.port}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        with self._lock:
            self._connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker. Return code: {rc}")
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages"""
        try:
            # Add message to queue for parallel processing
            if not self.message_queue.full():
                self.message_queue.put((msg.topic, msg.payload.decode('utf-8')))
            else:
                self.logger.warning("Message queue is full, dropping message")
                
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _process_messages(self):
        """Worker thread function to process messages"""
        while self._running:
            try:
                if not self.message_queue.empty():
                    topic, payload = self.message_queue.get(timeout=1)
                    
                    # Parse JSON payload
                    try:
                        data = json.loads(payload)
                        device_id = self._extract_device_id(topic)
                        
                        if device_id and self.data_callback:
                            self.data_callback(device_id, data)
                            
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                    
                    self.message_queue.task_done()
                        
            except Exception as e:
                if self._running:  # Only log if we're supposed to be running
                    self.logger.error(f"Error in message processing thread: {e}")
    
    def _extract_device_id(self, topic: str) -> Optional[str]:
        """Extract device ID from MQTT topic"""
        try:
            # Assuming topic format: sensors/{device_id}/data
            parts = topic.split('/')
            if len(parts) >= 2 and parts[0] == 'sensors':
                return parts[1]
            return None
        except Exception as e:
            self.logger.error(f"Error extracting device ID from topic {topic}: {e}")
            return None
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Wait for connection
            import time
            for _ in range(50):  # Wait up to 5 seconds
                if self._connected:
                    return True
                time.sleep(0.1)
            
            self.logger.error("Connection timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self._running = False
            
            # Wait for worker threads to finish
            for worker in self._workers:
                worker.join(timeout=2)
            
            self.client.loop_stop()
            self.client.disconnect()
            
            with self._lock:
                self._connected = False
                
            self.logger.info("Disconnected from MQTT broker")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    def subscribe_to_sensors(self, topic_pattern: str = "sensors/+/data") -> bool:
        """Subscribe to sensor data topics"""
        try:
            if not self._connected:
                self.logger.error("Not connected to MQTT broker")
                return False
            
            result, _ = self.client.subscribe(topic_pattern)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to topic: {topic_pattern}")
                return True
            else:
                self.logger.error(f"Failed to subscribe to topic: {topic_pattern}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error subscribing to sensors: {e}")
            return False
    
    def publish_alarm(self, alarm_data: Dict[str, Any], topic: str = "alarms/notifications") -> bool:
        """Publish alarm notification"""
        try:
            if not self._connected:
                self.logger.error("Not connected to MQTT broker")
                return False
            
            payload = json.dumps(alarm_data)
            result = self.client.publish(topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Published alarm notification: {alarm_data.get('rule_id', 'unknown')}")
                return True
            else:
                self.logger.error(f"Failed to publish alarm notification. Return code: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing alarm: {e}")
            return False
    
    def start_processing(self, num_workers: int = 4):
        """Start message processing threads"""
        try:
            self._running = True
            
            # Create worker threads for parallel message processing
            for i in range(num_workers):
                worker = threading.Thread(target=self._process_messages, name=f"MQTTWorker-{i}")
                worker.daemon = True
                worker.start()
                self._workers.append(worker)
            
            self.logger.info(f"Started {num_workers} MQTT processing workers")
            
        except Exception as e:
            self.logger.error(f"Error starting message processing: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker"""
        with self._lock:
            return self._connected