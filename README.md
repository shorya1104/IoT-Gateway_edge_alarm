# IoT Gateway Alarms Service

A high-performance, stateful alarm processing service for IoT Gateway systems that monitors sensor data from multiple devices and triggers alarms based on configurable rules.

## Features

- **Parallel Processing**: Handles 100+ devices simultaneously using multi-threading
- **Stateful Operation**: Maintains alarm states across application reboots using SQLite
- **Flexible Alarm Rules**: Supports simple threshold and conditional threshold alarms
- **Real-time Processing**: Processes MQTT sensor data with minimal latency
- **CLI Management**: Command-line interface for alarm rule configuration
- **Comprehensive Logging**: Full logging and error handling
- **MQTT Integration**: Subscribes to sensor data and publishes alarm notifications

## Architecture

The service consists of several key components:

- **MQTT Service**: Handles MQTT connections and message routing
- **Alarm Processor**: Core logic for alarm evaluation using thread pools
- **Storage Service**: SQLite-based persistence for rules and states
- **CLI Interface**: Command-line tools for alarm rule management

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd iot_gateway_alarms

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p data logs
```

### 2. Setup MQTT Broker

Ensure you have an MQTT broker running (e.g., Mosquitto):

```bash
# Install Mosquitto (Ubuntu/Debian)
sudo apt-get install mosquitto mosquitto-clients

# Start Mosquitto
sudo systemctl start mosquitto
```

### 3. Configuration

Edit `config/config.yaml` to match your environment:

```yaml
mqtt:
  broker: "localhost"
  port: 1883
  subscribe_topic: "sensors/+/data"
  alarm_topic: "alarms/notifications"

database:
  path: "data/alarms.db"

processing:
  max_workers: 20
  check_interval: 5
```

### 4. Create Sample Alarm Rules

```bash
# Setup sample rules for testing
python setup_sample_rules.py
```

### 5. Run the Service

```bash
# Start the alarm service
python src/main.py

# Or with custom config
python src/main.py --config config/config.yaml
```

### 6. Start Data Simulation

In another terminal:

```bash
# Start the provided data simulator
python data_simulate.py
```

## Alarm Rule Management

### Using the CLI

```bash
# List all alarm rules
python -m src.cli.alarm_cli list

# Add a simple threshold alarm
python -m src.cli.alarm_cli add-simple \
  "temp_high_office" \
  "device-1" \
  "temperature" \
  ">" \
  25.0 \
  5 \
  "Office temperature too high"

# Add a conditional alarm
python -m src.cli.alarm_cli add-conditional \
  "temp_high_when_on" \
  "device-2" \
  "temperature" \
  ">" \
  24.0 \
  3 \
  "device-2" \
  "current" \
  ">" \
  0 \
  "Temperature high when device is active"

# Show active alarms
python -m src.cli.alarm_cli active

# Delete an alarm rule
python -m src.cli.alarm_cli delete "temp_high_office"
```

## Alarm Types

### 1. Simple Threshold Alarms

Triggered when a sensor value exceeds a threshold for a specified duration.

**Example**: Temperature > 24°C for 60 minutes

### 2. Conditional Threshold Alarms

Triggered based on a primary condition AND an additional shunt condition.

**Example**: Temperature > 24°C for 60 minutes AND Current > 0 (device is on)

## Data Model

### Sensor Data Format

The service expects MQTT messages in the following JSON format:

```json
{
  "device_id": "device-1",
  "temperature": 25.5,
  "current": 1,
  "timestamp": 1703123456
}
```

### MQTT Topics

- **Subscribe**: `sensors/{device_id}/data`
- **Publish**: `alarms/notifications`

## Performance

The service is designed to handle:

- **100+ devices** in parallel
- **Sub-second processing** latency
- **Persistent state** across reboots
- **Thread-safe** operations

## Testing

### Run Unit Tests

```bash
# Run the test suite
python tests/test_alarm_processor.py
```

### Manual Testing

1. Start the alarm service
2. Run the data simulator
3. Use the CLI to create test rules
4. Monitor logs for alarm triggers

## Configuration Options

### MQTT Settings

```yaml
mqtt:
  broker: "localhost"          # MQTT broker hostname
  port: 1883                   # MQTT broker port
  username: null               # Optional username
  password: null               # Optional password
  client_id: "alarm_service"   # MQTT client ID
  subscribe_topic: "sensors/+/data"  # Topic pattern to subscribe
  alarm_topic: "alarms/notifications" # Topic for publishing alarms
```

### Database Settings

```yaml
database:
  path: "data/alarms.db"       # SQLite database file path
```

### Processing Settings

```yaml
processing:
  max_workers: 20              # Maximum thread pool workers
  batch_size: 50               # Batch processing size
  check_interval: 5            # Status check interval (seconds)
```

### Logging Settings

```yaml
logging:
  level: "INFO"                # Log level (DEBUG, INFO, WARNING, ERROR)
  file: "logs/app.log"         # Log file path
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Error Handling

The service includes comprehensive error handling:

- **MQTT Connection**: Automatic reconnection attempts
- **Database Operations**: Transaction rollback on failures
- **Processing Errors**: Isolated error handling per device
- **Graceful Shutdown**: Signal handling for clean shutdown

## Monitoring

### Log Messages

The service logs important events:

- Alarm triggers and clearances
- Device connection status
- Processing statistics
- Error conditions

### Status Information

Real-time status includes:

- Number of active devices
- Active alarm count
- Processing queue status

## Architecture Decisions

### Storage: SQLite

- **Pros**: Lightweight, embedded, ACID compliance
- **Cons**: Single-writer limitation (mitigated by connection pooling)
- **Alternative**: Could use Redis for higher throughput

### Threading: ThreadPoolExecutor

- **Pros**: Efficient parallel processing, bounded resource usage
- **Cons**: GIL limitations for CPU-bound tasks
- **Alternative**: Process-based parallelism for CPU-intensive workloads

### MQTT: Paho MQTT Client

- **Pros**: Mature, well-documented, reliable
- **Cons**: Synchronous callbacks (mitigated by queuing)
- **Alternative**: Async MQTT clients for higher concurrency

## Scaling Considerations

For larger deployments:

1. **Database**: Consider PostgreSQL or Redis for higher concurrency
2. **Messaging**: Use message brokers like RabbitMQ or Apache Kafka
3. **Processing**: Implement distributed processing with Celery
4. **Monitoring**: Add Prometheus metrics and Grafana dashboards

## License

This project is open source. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For questions or issues:

1. Check the logs in `logs/app.log`
2. Run tests to verify functionality
3. Review configuration settings
4. Open an issue on GitHub
