import json
import random
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"   # Change if your broker is remote
PORT = 1883
BASE_TOPIC = "sensors"  # Our app subscribes to sensors/<device_id>/data
NUM_DEVICES = 100

def main():
    client = mqtt.Client(client_id="simulator")
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            for i in range(1, NUM_DEVICES + 1):
                device_id = f"device-{i}"

                # Simulated sensor values
                temperature = round(random.uniform(20, 35), 2)  # °C
                current = random.choice([0, 1])                 # 0=off, 1=on

                payload = {
                    "device_id": device_id,
                    "temperature": temperature,
                    "current": current,
                    "timestamp": int(time.time())
                }

                topic = f"{BASE_TOPIC}/{device_id}/data"
                client.publish(topic, json.dumps(payload))
                print(f"Published to {topic}: {payload}")

            # Wait before next round of updates
            time.sleep(5)

    except KeyboardInterrupt:
        print("Simulation stopped by user")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
