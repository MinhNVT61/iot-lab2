import os, json
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt
load_dotenv()
FIELDS = ["temperature", "humidity", "distance_cm"]
def db():
    return InfluxDBClient(url=os.environ["INFLUX_URL"], token=os.environ["INFLUX_TOKEN"], org=os.environ["INFLUX_ORG"])
def mqtt_client(client_id):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if os.getenv("MQTT_USER"):
        c.username_pw_set(os.environ["MQTT_USER"], os.getenv("MQTT_PASSWORD", ""))
    if os.getenv("MQTT_TLS", "false").lower() == "true":
        c.tls_set()
    c.reconnect_delay_set(1, 30)
    return c
def connect(c):
    c.connect(os.environ["MQTT_HOST"], int(os.getenv("MQTT_PORT", "1883")), 60)
def read_data(client, measurement, hours=1):
    import pandas as pd
    bucket = json.dumps(os.environ["INFLUX_BUCKET"])
    query = f'from(bucket: {bucket}) |> range(start: -{int(hours)}h) |> filter(fn: (r) => r._measurement == "{measurement}") |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")'
    frames = client.query_api().query_data_frame(query)
    if isinstance(frames, list):
        frames = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not frames.empty:
        frames["_time"] = pd.to_datetime(frames["_time"], utc=True)
    return frames
