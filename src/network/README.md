# NETWORK MODULE – Unreliable Network Simulator + Logging

## 1. Mục tiêu
Mô phỏng mạng không tin cậy theo yêu cầu:
- delay
- drop
- duplicate
- reorder
- limit throughput
- block/unblock peer
- log mọi event (send, delay, drop…)

Network chỉ xử lý “message”, không hiểu nội dung.

---

## 2. Cấu trúc thư mục
network/
├─ messages.py
├─ network.py
└─ logging_utils.py


---

## 3. File chi tiết

### `messages.py`
- Định nghĩa loại message:
  - TX
  - BLOCK_HEADER
  - BLOCK_BODY
  - VOTE
- Message object chứa from → to → payload

### `network.py`
- Event queue (priority queue)
- Simulate delay/drop/dup/reorder
- Throttle outbound rate
- Ghi log toàn bộ event với timestamp + nodeID + height
- deliver_message() gọi Node.receive()

### `logging_utils.py`
- Helper ghi log dạng JSON lines
- Bảo đảm deterministic log formatting

---

## 4. Test module
pytest tests/test_network.py