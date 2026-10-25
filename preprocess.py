import argparse, os, math
from pathlib import Path
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from common import db, read_data
from processing import process
def main(hours=1):
    with db() as client:
        raw=read_data(client,"sensor_raw",hours)
        if raw.empty: print("Chưa có dữ liệu thô"); return
        out=process(raw)
        Path("data").mkdir(exist_ok=True)
        out.to_csv("data/processed.csv",index=False)
        writer=client.write_api(write_options=SYNCHRONOUS)
        points=[]
        # Include all numeric fields; undefined values use explicit validity fields.
        for row in out.to_dict("records"):
            p=Point("sensor_processed").tag("device_id",row["device_id"]).tag("pipeline_version","v1").time(row["_time"].to_pydatetime(),WritePrecision.MS)
            for k,v in row.items():
                if k in ("_time","device_id"): continue
                ok=math.isfinite(float(v)); p.field(k+"_valid",ok).field(k,float(v) if ok else 0.0)
            points.append(p)
        writer.write(bucket=os.environ["INFLUX_BUCKET"],record=points)
        print(f"Đọc {len(raw)} điểm, ghi {len(out)} cửa sổ. CSV: data/processed.csv")
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--hours",type=int,default=1)
    main(parser.parse_args().hours)
