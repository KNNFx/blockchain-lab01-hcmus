# NODE & NETWORK MODULE – Simulator • Node Logic • Logging

## 1. Mục tiêu
Triển khai môi trường chạy toàn hệ thống:
- Network mô phỏng không tin cậy
- Node xử lý block, vote, tx
- Logging tất cả sự kiện
- End-to-end simulation

---

## 2. Thành phần thư mục
node_network/
├─ messages.py
├─ network.py
├─ node.py
└─ simulator.py


---

## 3. Nhiệm vụ từng file

### `messages.py`
- Định nghĩa:
  - TX message
  - BLOCK_HEADER
  - BLOCK_BODY
  - VOTE
- Cấu trúc message để simulator xử lý.

---

### `network.py`
- Mạng mô phỏng:
  - delay
  - drop
  - duplicate
  - reorder
  - limit throughput
  - block/unblock peer
- Log:
  - send, deliver, drop → timestamp, node ID, height
- Event queue dựa trên priority queue.

---

### `node.py`
- Glue code:
  - Nhận message từ network
  - Validate block (module blocklayer)
  - Apply tx (module core)
  - Gọi consensus (module consensus)
  - Gửi vote / block header / block body
- Lưu local ledger + local state.

---

### `simulator.py`
- Tạo N node (≥8)
- Kết nối network
- Load config từ YAML
- Chạy mô phỏng cho đến khi đủ block finalized
- Xuất log vào `logs/runX/`

---

## 4. Trách nhiệm người phụ trách module
- Đảm bảo simulator chạy deterministic khi cùng config.
- Log đầy đủ để so sánh run1 vs run2.
- Không thay đổi logic crypto/block/state/consensus.

---

## 5. Test end-to-end
pytest tests/test_end_to_end.py

## 6. Chạy simulator
python src/main.py config/default_config.yaml