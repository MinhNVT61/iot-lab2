import json
from pathlib import Path
import pandas as pd
import streamlit as st
from common import db, read_data, FIELDS
st.set_page_config(page_title="IoT Bài 2",layout="wide")
st.title("IoT • Thu thập và tiền xử lý")
st.caption("Wokwi ESP32 · DHT22 · HC-SR04 | Chu kỳ đo 5 giây")
hours=st.sidebar.selectbox("Khoảng xem (giờ)",[1,3,6,24])
@st.fragment(run_every="5s")
def monitor():
    try:
        with db() as c: raw=read_data(c,"sensor_raw",hours); processed=read_data(c,"sensor_processed",hours)
    except Exception as e: st.error(f"Không đọc được InfluxDB ({type(e).__name__}). Kiểm tra .env và Docker."); return
    if raw.empty: st.info("Chưa có dữ liệu. Hãy chạy collector và Wokwi/simulator."); return
    device=st.selectbox("Thiết bị",sorted(raw.device_id.unique()))
    r=raw[raw.device_id==device].sort_values("_time")
    last=r.iloc[-1]
    age=(pd.Timestamp.now(tz="UTC")-pd.to_datetime(last.received_at,utc=True)).total_seconds()
    st.success("Thiết bị đang gửi dữ liệu") if age<20 else st.warning(f"Không có bản tin mới trong {age:.0f} giây")
    for col,key,unit in zip(st.columns(3),FIELDS,["°C","%RH","cm"]): col.metric(key,f"{last[key]:.2f} {unit}")
    a,b,c=st.tabs(["Dữ liệu thô","Đã xử lý","Hiệu năng"])
    with a:
        for k in FIELDS: st.line_chart(r.set_index("_time")[[k]])
        st.dataframe(r.tail(30),hide_index=True)
    with b:
        if processed.empty: st.info("Chạy python preprocess.py --hours 1 để tạo dữ liệu xử lý.")
        else:
            q=processed[processed.device_id==device].copy().sort_values("_time")
            for k in FIELDS:
                q.loc[~q[k+"_valid"].astype(bool),k]=float("nan")
                st.line_chart(q.set_index("_time")[[k,k+"_rolling_mean"]])
            st.dataframe(q[["_time","sample_count","missing_count","outlier_count"]],hide_index=True)
    with c:
        positive=r.loc[r.latency_ms>=0,"latency_ms"]
        st.write("Độ trễ đo → collector; chưa gồm thời gian ghi DB và cập nhật giao diện.")
        if len(positive):
            x,y=st.columns(2); x.metric("Trung vị",f"{positive.median():.1f} ms"); y.metric("p95",f"{positive.quantile(.95):.1f} ms")
        st.write("Bản tin có độ trễ âm:",int((r.latency_ms<0).sum()))
        gaps=sum(int(g.sequence.sort_values().diff().sub(1).clip(lower=0).sum()) for _,g in r.groupby("boot_id"))
        st.write("Khoảng trống sequence trong khoảng xem:",gaps)
        if Path("data/stats.json").exists(): st.json(json.loads(Path("data/stats.json").read_text()))
        st.caption("Thống kê collector tính từ lần chạy hiện tại. Sequence reset được tách theo boot_id.")
monitor()
