# Bài thực hành 2 — IoT và Ứng dụng

Bộ mã nguồn phát triển từ mạch Wokwi bài 1: ESP32 + DHT22 GPIO15 + HC-SR04 GPIO5/18 + LED GPIO2. Đây là bộ triển khai để chạy thực nghiệm, không chứa số liệu đo hoặc ảnh demo đã có sẵn.

## Kiến trúc
Wokwi → broker MQTT → collector Python → InfluxDB sensor_raw → preprocessing → sensor_processed → Streamlit.

## 1. Chạy thử trên Windows bằng simulator
Cài Python 3.11/3.12, Docker Desktop và Git. Mở PowerShell trong thư mục đã giải nén:

```powershell
Copy-Item .env.example .env
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
Sửa `.env`: đặt INFLUX_PASSWORD ít nhất 12 ký tự và INFLUX_TOKEN thành chuỗi ngẫu nhiên dài; không dùng giá trị mẫu. Giữ MQTT_HOST=localhost để chạy thử local.

```powershell
docker compose up -d
```
Chờ InfluxDB khởi động, mở http://localhost:8086. Đăng nhập `student` và mật khẩu trong `.env`. Bucket `iot_lab2`, org `iot-lab`, retention 7 ngày. Các biến khởi tạo chỉ có tác dụng với volume mới; đổi `.env` không tự đổi tài khoản/bucket đã tồn tại.

Mở các cửa sổ PowerShell riêng, cùng thư mục dự án:

```powershell
# Cửa sổ 1
.venv\Scripts\python.exe collector.py
# Cửa sổ 2
.venv\Scripts\python.exe simulator.py
# Cửa sổ 3
.venv\Scripts\python.exe -m streamlit run app.py
```
Mở http://localhost:8501. Sau 10–15 phút, chạy tại cửa sổ khác:

```powershell
.venv\Scripts\python.exe preprocess.py --hours 1
```
Dashboard tự tải lại dữ liệu mỗi 5 giây; preprocessing cần chạy lại thủ công khi muốn cập nhật. Trên Linux/macOS dùng `python3 -m venv .venv` và `.venv/bin/python`.

## 2. Nối Wokwi thay simulator
Wokwi Public Gateway không vào được Mosquitto local bằng localhost/IP LAN. Chọn:
- Broker MQTT trên Internet do giảng viên cung cấp, cùng host/topic/auth ở firmware và `.env`.
- Hoặc Wokwi Private Gateway để vào broker local. Broker trong Compose chỉ bind loopback để thử local; nếu cần LAN phải cấu hình listener/binding, xác thực và firewall phù hợp.

Dừng simulator trước khi chạy Wokwi để tránh trộn hai nguồn có cùng device_id. Sao chép `firmware/diagram.json`, `libraries.txt`, `sketch.ino` vào dự án Wokwi. Tạo `secrets.h` từ `secrets.example.h`, điền broker. Không dùng thingsboard.cloud làm broker subscribe thông thường của collector.

Firmware mẫu dùng TCP 1883, chỉ phù hợp broker cho phép MQTT không TLS trong lab. Nếu broker yêu cầu 8883/TLS, phải thay WiFiClient bằng WiFiClientSecure, nạp CA tin cậy của broker và đồng bộ NTP trước kết nối TLS; không dùng setInsecure. Python đã hỗ trợ MQTT_TLS=true với CA hệ thống. Không chỉ đổi cổng firmware sang 8883.

Chạy mô phỏng, chờ NTP và MQTT connected. Thay đổi DHT22 và HC-SR04 rồi xác nhận dashboard thay đổi. Khi chuyển sang ESP32 thật, thay SSID/mật khẩu; dùng chia áp ECHO HC-SR04 để bảo vệ GPIO 3.3V.

## 3. JSON và schema
Topic `iot/bai2/esp32-01/telemetry`; các trường device_id, boot_id, sequence, timestamp UTC, temperature °C, humidity %RH, distance_cm cm, rssi dBm, uptime_s.

`sensor_raw`: tag device_id; fields các giá trị đo, sequence (int), boot_id (string), latency_ms và received_at. Timestamp là thời điểm đo, độ chính xác ms. Không dùng sequence/boot_id làm tag để tránh cardinality cao. Trong một thiết bị, timestamp phải duy nhất; InfluxDB gộp điểm cùng measurement/tags/time.

`sensor_processed`: tags device_id, pipeline_version=v1; fields trung bình mỗi phút, rolling mean 5 cửa sổ, delta, scaled, sample_count, missing_count, outlier_count. Timestamp đầu cửa sổ phút. Field `_valid` thể hiện giá trị có xác định không; placeholder 0 phải đọc cùng cờ này. App đã áp dụng cờ cho giá trị cảm biến.

## 4. Tiền xử lý và giới hạn
Đối chiếu lưới 5s; IQR theo từng thiết bị/biến trên khoảng truy vấn; khi IQR=0, giá trị khác trung vị được đánh dấu. Chỉ nội suy khoảng thiếu nội bộ <=2 mẫu; khoảng dài giữ thiếu. Resampling 1 phút, rolling mean 5 phút, delta và StandardScaler fit trên cửa sổ truy vấn hiện tại.

Scaled dùng để phân tích batch, không so sánh trực tiếp giữa các khoảng truy vấn khác nhau. Khi triển khai lâu dài nên fit và lưu scaler cố định trên tập calibration. IQR có thể nhầm biến đổi thật thành outlier; cần so sánh biểu đồ và bối cảnh cảm biến. Cửa sổ đầu/cuối có thể chưa đủ một phút; missing_count chỉ tính trong khoảng từ điểm đầu đến cuối quan sát, không suy ra mất mẫu ngoài khoảng này. Không nội suy qua ranh giới khởi động lại được đảm bảo ở bản này; nên bổ sung phân đoạn boot_id nếu cần.

Collector lưu SQLite trước ghi DB, chống trùng theo device_id/boot_id/sequence qua khởi động lại collector, retry DB theo vòng lặp. Spool tăng dần và cần dọn/archive cho triển khai dài hạn. MQTT vẫn có thể mất dữ liệu khi collector offline; firmware PubSubClient publish QoS0, subscribe QoS1 không nâng QoS của publisher. `publish=OK` chỉ là kết quả gửi client, chưa chứng minh DB lưu thành công. Nên bổ sung MQTT QoS1 publisher, persistent session, ACK hoặc buffer thiết bị nếu cần độ tin cậy cao.

latency_ms đo từ lúc lấy mẫu đến collector, phụ thuộc đồng bộ NTP và thời gian mô phỏng; không phải độ trễ đến màn hình. Không đưa độ trễ âm vào trung vị/p95; app đếm riêng để kiểm tra đồng hồ. Đo end-to-end thực sự cần instrument thêm DB và UI. Thống kê collector reset mỗi lần chạy; sequence gap chỉ quan sát giữa các bản tin trong cùng boot_id.

## 5. Thực nghiệm
1. Bình thường 15 phút: khoảng 180 bản tin nếu gửi đúng 5s; dùng số đếm thật.
2. Dừng Wokwi >20s: app báo offline; chạy lại tạo boot_id mới.
3. Chạy simulator.py --faults (nguồn giả lập): tạo trùng, JSON sai, khoảng thiếu và nhiệt độ bất thường.
4. `docker compose stop influxdb`: giữ collector chạy; quan sát DB errors và spool. `docker compose start influxdb`: kiểm tra ghi bù.
5. Chạy preprocess, xem dữ liệu xử lý, chụp ảnh từng tab.
6. Lưu CSV và số liệu thật; tuyệt đối không gọi dữ liệu simulator là đo phần cứng.

## 6. GitHub và sản phẩm nộp
Tạo repository của bạn, chạy `git init`, `git add .`, `git commit -m "Implement IoT lab 2"`, thêm remote và push theo hướng dẫn GitHub. Kiểm tra token/mật khẩu không xuất hiện trong commit, secrets.h không upload. Không có tài khoản/remote được cung cấp nên bộ này chưa được đẩy lên GitHub.

Nộp source, liên kết Wokwi, app Streamlit và báo cáo Word 4–6 trang dựa trên `BAO_CAO_KHUNG.md`. Bộ này chưa có báo cáo Word hoàn chỉnh vì cần kết quả thực nghiệm của bạn.

## Tài liệu chính thức
- https://docs.wokwi.com/guides/esp32-wifi
- https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
- https://docs.influxdata.com/influxdb/v2/install/use-docker-compose/
- https://thingsboard.io/docs/reference/mqtt-api/telemetry/
