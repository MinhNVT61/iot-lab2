# Báo cáo Bài thực hành 2 — khung 5 trang
Họ tên: … | MSSV: … | Lớp: … | Ngày: …

## Trang 1 — Mục tiêu và kiến trúc
Mô tả kế thừa ESP32/DHT22/HC-SR04 từ bài 1. Vẽ sơ đồ Wokwi → MQTT → Python → InfluxDB → preprocessing → Streamlit. Nêu rõ mô phỏng hay phần cứng thật, broker và môi trường thực tế đã dùng.

## Trang 2 — Thu thập và lưu trữ
Chèn JSON thật đã che thông tin xác thực. Mô tả topic, chu kỳ 5s, validation, schema tags/fields/timestamp, retention 7 ngày, chống trùng và SQLite spool. Chèn ảnh InfluxDB có dữ liệu.

## Trang 3 — Tiền xử lý
Trình bày missing, IQR, nội suy ngắn, resampling 1 phút, rolling mean, delta, StandardScaler. Chèn bảng/biểu đồ trước sau lấy từ dữ liệu chạy thật; giải thích các giới hạn trong README.

## Trang 4 — Kết quả và dashboard
Chèn ảnh ba tab và bảng:
| Chỉ số | Kết quả thật |
|---|---|
| Thời gian thực nghiệm | … |
| Received / Written / Invalid / Duplicate | … |
| Khoảng trống sequence | … |
| Độ trễ collector trung vị / p95 | … |
| Số điểm thô / cửa sổ phút | … |
| Kết quả DB dừng và phục hồi | … |
Phân biệt số liệu giả lập với Wokwi; không tự điền kết quả.

## Trang 5 — Phân tích và cải tiến
Phân tích QoS0, lỗi đồng bộ đồng hồ, spool tăng, cửa sổ phút thiếu, IQR nhầm biến đổi thật, scaler theo batch. Đề xuất TLS, QoS1, persistent session, scaler calibration và preprocessing theo lịch. Nêu khó khăn đã gặp và cách giải quyết thực tế. Kết luận mức độ hoàn thành các yêu cầu.
