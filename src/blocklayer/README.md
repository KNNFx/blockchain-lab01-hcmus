# BLOCKLAYER MODULE – Block • BlockHeader • Validation • Ledger

## 1. Mục tiêu
Module này định nghĩa cấu trúc block và thực thi:
- Tạo block mới
- Validate block nhận được
- Lưu chuỗi block và state vào Ledger
- Tính block hash và state hash nhất quán

---

## 2. Thành phần thư mục
blocklayer/
├─ block.py
└─ ledger.py

---

## 3. Nhiệm vụ từng file

### `block.py`
- Struct:
  - `BlockHeader(height, parent_hash, state_hash, proposer_pubkey_hex)`
  - `Block(header, txs, header_signature)`
- Hàm:
  - `build_block(parent_block, parent_state, txs, proposer_keypair)`
  - `validate_block(block, parent_block, parent_state)`
- Yêu cầu:
  - Re-execute txs bằng State của module core
  - So khớp `state_hash`
  - Verify chữ ký header
  - Hash block từ canonical encoding

---

### `ledger.py`
- Lưu trữ:
  - block theo height
  - state sau mỗi block
- Hàm:
  - `add_block(block, state_after)`
  - `get_block(height)`
  - `get_state(height)`
  - `latest_finalized()`

---

## 4. Trách nhiệm người phụ trách module
- Đảm bảo block hợp lệ tuyệt đối.
- Đảm bảo build/validate sử dụng đúng hàm từ module core.
- Không triển khai logic consensus ở đây.

---

## 5. Test nhanh
pytest tests/test_block_layer.py