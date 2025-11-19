# BLOCKLAYER MODULE – Block • BlockHeader • Validation • Ledger

## 1. Mục tiêu
Module này định nghĩa:
- BlockHeader
- Block
- Block creation (build_block)
- Block validation (validate_block)
- Ledger quản lý block & state theo height

Dựa hoàn toàn vào module `core`.

---

## 2. Cấu trúc thư mục
blocklayer/
├─ block.py
└─ ledger.py

---

## 3. File chi tiết

### `block.py`
- Struct:
  - BlockHeader(height, parent_hash, state_hash, proposer_pubkey_hex)
  - Block(header, txs, header_signature)
- Hàm:
  - build_block(parent_block, parent_state, txs, keypair)
  - validate_block(block, parent_block, parent_state)
- Yêu cầu:
  - Re-execute txs bằng State của core
  - verify chữ ký header
  - block_hash = sha256(canonical_json(header))

### `ledger.py`
- Lưu block theo height
- Lưu state sau mỗi block
- Hàm:
  - add_block(block, state_after)
  - get_block(height)
  - get_state(height)
  - latest_finalized()

---

## 4. Test module
pytest tests/test_blocklayer.py