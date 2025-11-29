# NODE + SIMULATOR MODULE – Glue Logic • E2E Runner • Determinism Check

## 1. Mục tiêu
Kết nối toàn bộ hệ thống:
- Node class xử lý message inbound/outbound
- Simulator chạy nhiều node, nhiều round
- Gọi Network simulator
- Gắn Core + BlockLayer + Consensus lại với nhau
- Thực thi end-to-end tests
- Kiểm tra determinism (run1 == run2)
- Đảm bảo mọi message được verify signature với đúng domain context
- Log đầy đủ mọi event để reproduce và debug

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
**Chức năng chính:**
- Nhận message từ network (headers trước, bodies sau khi header được accept)
- **Verify signature** cho mọi message với đúng domain context:
  - Transactions: `TX:chain_id`
  - Block headers: `HEADER:chain_id`
  - Votes (Prevote/Precommit): `VOTE:chain_id`
- Gọi `blocklayer.validate_block()` để kiểm tra block structure và parent hash
- Gọi consensus để nhận/gửi vote (Prevote và Precommit)
- Quản lý mempool (pending transactions)
- Propose block khi tới lượt làm proposer
- **Rate limiting**: giới hạn outbound message rate và block peers quá tải
- Reject duplicates, replays, và invalid signatures
- Log mọi action với timestamp để debug

### `simulator.py`
**Chức năng chính:**
- Khởi tạo **tối thiểu 8 nodes** (configurable via YAML)
- Kết nối với network simulator (random delays hoặc file-driven patterns)
- Load config từ `config/default_config.yaml`:
  - Số lượng nodes
  - Network delay patterns (min/max delay, drop rate)
  - Validator set và public keys
  - Chain ID
- **Vòng lặp event-driven:**
  - Gọi `network.tick()` để xử lý message queue
  - Nodes xử lý inbound messages
  - Nodes gửi outbound messages (headers → bodies)
  - Log mọi network event: **send, drop, delay, block, unblock**
  - Log format: `timestamp | node_id | event_type | height | details`
- Kết thúc khi đủ số block finalized (hoặc timeout)
- Export logs ra `logs/` directory với timestamp
- Hỗ trợ pause/resume cho debugging

### `determinism.py`
**Chức năng chính:**
- Chạy simulator **2 lần** với cùng config và random seed
- So sánh **byte-by-byte** hai file log:
  - Mọi network event phải giống hệt nhau
  - Mọi consensus decision phải giống hệt nhau
  - Timestamps và ordering phải identical
- So sánh **final state hash** của mọi node:
  - State commitment hash phải giống nhau
  - Block sequence phải giống nhau
  - Finalized heights phải giống nhau
- In kết quả chi tiết ra `logs/run_compare.txt`:
  -  PASS nếu logs và state hash identical
  - FAIL nếu có bất kỳ khác biệt nào (kèm diff)
- Script này là **bằng chứng chính** cho tính đúng đắn của hệ thống
- Đảm bảo deterministic encoding cho mọi data structure

**Yêu cầu:**
- Cùng config → cùng kết quả (no randomness leak)
- Field order, endianness, string encoding phải consistent
- Hash và signature generation phải deterministic

---

## 4. Test module (E2E)

### Unit Tests (`tests/test_e2e.py`)
- **Signature verification:** kiểm tra domain separation (TX/HEADER/VOTE contexts)
- **State update rules:** deterministic execution với cùng tx sequence
- **Vote counting:** đếm đúng Prevote/Precommit, reject invalid votes
- **Block validation:** parent hash, height sequence, state commitment

### End-to-End Tests (bắt buộc theo PDF)
Phải cover **5 test cases chính:**

1. **Safety Test:** Chỉ 1 block được finalized tại mỗi height
   - Setup: 8+ nodes, normal network
   - Expected: Không có 2 blocks khác nhau cùng height được finalized

2. **Invalid Signature Test:** Messages với signature sai bị reject
   - Test: Gửi tx/vote/header với signature không hợp lệ
   - Expected: Reject ngay, không ảnh hưởng state hoặc consensus

3. **Wrong Context Test:** Signature từ context này không dùng được cho context khác
   - Test: Dùng TX signature cho VOTE message
   - Expected: Reject do domain separation

4. **Replay/Duplicate Test:** Replays và duplicates bị ignore
   - Test: Gửi cùng message nhiều lần
   - Expected: Chỉ process 1 lần, không break safety

5. **Network Delay Test:** Delayed/dropped messages không gây conflict
   - Test: Random delays, packet drops (theo config)
   - Expected: Liveness có thể chậm nhưng safety luôn đảm bảo

### Determinism Test
- **Run twice, compare everything:**
  - Logs phải byte-identical
  - Final state hash phải giống nhau
  - Block sequence phải giống nhau

**Chạy test:**
```bash
pytest tests/test_e2e.py -v
```

---

## 5. Chạy toàn hệ thống

### Chạy simulator với config mặc định:
```bash
python src/main.py config/default_config.yaml
```

### Chạy determinism check:
```bash
python src/node_sim/determinism.py
```

### Các file log được tạo:
- `logs/run1_TIMESTAMP.log` - Log của run đầu tiên
- `logs/run2_TIMESTAMP.log` - Log của run thứ hai
- `logs/run_compare.txt` - Kết quả so sánh (PASS/FAIL)
- `logs/network_events.log` - Chi tiết mọi network event

### Config parameters quan trọng (config/default_config.yaml):
```yaml
network:
  num_nodes: 8              # Tối thiểu 8 nodes
  min_delay_ms: 10
  max_delay_ms: 100
  drop_rate: 0.05           # 5% packet loss
  rate_limit_msg_per_sec: 100

consensus:
  chain_id: "test-chain-01"  # Dùng cho domain separation
  
simulator:
  max_blocks: 10
  timeout_sec: 60
  random_seed: 42           # Cố định để deterministic
```