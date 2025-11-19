# NODE + SIMULATOR MODULE – Glue Logic • E2E Runner • Determinism Check

## 1. Mục tiêu
Kết nối toàn bộ hệ thống:
- Node class xử lý message inbound/outbound
- Simulator chạy nhiều node, nhiều round
- Gọi Network simulator
- Gắn Core + BlockLayer + Consensus lại với nhau
- Thực thi end-to-end tests
- Kiểm tra determinism (run1 == run2)

Người 5 không cần chờ module khác – có thể dùng mock trước.

---

## 2. Cấu trúc thư mục
node_sim/
├─ node.py
├─ simulator.py
└─ determinism.py


---

## 3. File chi tiết

### `node.py`
- Nhận message từ network
- Gọi blocklayer.validate_block()
- Gọi consensus nhận vote / gửi vote
- Quản lý mempool
- Propose block khi tới lượt

### `simulator.py`
- Khởi tạo N node
- Kết nối với network simulator
- Load config YAML
- Vòng lặp event:
  - network.tick()
  - nodes xử lý message
- Kết thúc khi đủ block finalized

### `determinism.py`
- Chạy simulator 2 lần
- So log byte-by-byte
- So state hash cuối
- In kết quả ra `logs/run_compare.txt`

---

## 4. Test module (E2E)
pytest tests/test_e2e.py

---

## 5. Chạy toàn hệ thống
python src/main.py config/default_config.yaml