import json, math, os, sqlite3, time, logging
from pathlib import Path
from datetime import datetime, timezone
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from common import db, mqtt_client, connect
Path("data").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
sql = sqlite3.connect("data/spool.sqlite")
sql.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT, received TEXT, sent INTEGER DEFAULT 0)")
sql.commit()
stats = {"received": 0, "invalid": 0, "duplicate": 0, "written": 0, "db_errors": 0}
def validate(d):
    for k in ["device_id", "boot_id"]:
        if not isinstance(d.get(k), str) or not d[k] or len(d[k]) > 64: raise ValueError(k)
    if type(d.get("sequence")) is not int or d["sequence"] < 0: raise ValueError("sequence")
    for k in ["temperature", "humidity", "distance_cm", "rssi", "uptime_s"]:
        if type(d.get(k)) not in (int, float) or not math.isfinite(d[k]): raise ValueError(k)
    if not -40 <= d["temperature"] <= 80 or not 0 <= d["humidity"] <= 100 or not 2 <= d["distance_cm"] <= 400: raise ValueError("sensor range")
    t = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
    if t.tzinfo is None: raise ValueError("timestamp requires timezone")
    if abs((datetime.now(timezone.utc)-t).total_seconds()) > 86400: raise ValueError("clock exceeds 24h")
    return t
def on_connect(c, userdata, flags, reason, properties):
    logging.info("MQTT connect: %s", reason)
    if not reason.is_failure: c.subscribe(os.environ["MQTT_TOPIC"], qos=1)
def on_message(c, userdata, msg):
    stats["received"] += 1
    try:
        d=json.loads(msg.payload); validate(d)
        key=json.dumps([d["device_id"], d["boot_id"], d["sequence"]])
        sql.execute("INSERT INTO events(id,payload,received) VALUES(?,?,?)", (key,json.dumps(d),datetime.now(timezone.utc).isoformat()))
        sql.commit()
    except sqlite3.IntegrityError: stats["duplicate"] += 1
    except (ValueError, TypeError, KeyError, UnicodeError):
        stats["invalid"] += 1; logging.warning("Rejected invalid payload")
def main():
    client=db(); writer=client.write_api(write_options=SYNCHRONOUS)
    mqtt=mqtt_client("lab2-collector"); mqtt.on_connect=on_connect; mqtt.on_message=on_message
    connect(mqtt)
    try:
        while True:
            mqtt.loop(timeout=0.2)
            for key,payload,received in sql.execute("SELECT id,payload,received FROM events WHERE sent=0 ORDER BY rowid LIMIT 50").fetchall():
                d=json.loads(payload); t=datetime.fromisoformat(d["timestamp"].replace("Z","+00:00"))
                latency=(datetime.fromisoformat(received)-t).total_seconds()*1000
                point=Point("sensor_raw").tag("device_id",d["device_id"]).time(t,WritePrecision.MS)
                for k in ["temperature","humidity","distance_cm","rssi","uptime_s"]: point.field(k,float(d[k]))
                point.field("sequence",int(d["sequence"])).field("boot_id",d["boot_id"]).field("latency_ms",latency).field("received_at",received)
                try:
                    writer.write(bucket=os.environ["INFLUX_BUCKET"],record=point)
                    sql.execute("UPDATE events SET sent=1 WHERE id=?",(key,)); sql.commit(); stats["written"]+=1
                except Exception as e:
                    stats["db_errors"]+=1; logging.error("DB write failed (%s); kept in spool",type(e).__name__); time.sleep(1); break
            Path("data/stats.json").write_text(json.dumps(stats))
            if not mqtt.is_connected():
                try: mqtt.reconnect()
                except OSError: time.sleep(1)
    except KeyboardInterrupt: pass
    finally: mqtt.disconnect(); client.close(); sql.close()
if __name__ == "__main__": main()
