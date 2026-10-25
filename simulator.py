import json, time, uuid, math, os, argparse
from datetime import datetime, timezone
from common import mqtt_client, connect
parser=argparse.ArgumentParser(); parser.add_argument("--faults",action="store_true"); args=parser.parse_args()
c=mqtt_client("lab2-simulator-"+uuid.uuid4().hex[:8]); connect(c); c.loop_start()
boot=uuid.uuid4().hex; seq=0
try:
    while True:
        seq+=1
        d=dict(device_id="esp32-01",boot_id=boot,sequence=seq,timestamp=datetime.now(timezone.utc).isoformat(),temperature=25+2*math.sin(seq/10),humidity=60+5*math.sin(seq/13),distance_cm=100+10*math.sin(seq/7),rssi=-50,uptime_s=seq*5)
        if args.faults and seq%17==0: time.sleep(5); continue
        if args.faults and seq%13==0: d["temperature"]=75
        payload=json.dumps(d)
        c.publish(os.environ["MQTT_TOPIC"],payload,qos=1).wait_for_publish()
        if args.faults and seq%11==0: c.publish(os.environ["MQTT_TOPIC"],payload,qos=1).wait_for_publish()
        if args.faults and seq%19==0: c.publish(os.environ["MQTT_TOPIC"],'{"humidity":"bad"}',qos=1)
        print(seq,d["temperature"]); time.sleep(5)
except KeyboardInterrupt: pass
finally: c.disconnect(); c.loop_stop()
