# CORE MODULE – Crypto • Encoding • Transactions • State

## 1. Mục tiêu
Module này cung cấp toàn bộ “lõi” của hệ thống blockchain:
- Mã hóa determinisitc (canonical encoding)
- Chữ ký và xác minh chữ ký (Ed25519 hoặc secp256k1)
- Cấu trúc Transaction + SignedTransaction
- Mô hình State dạng key–value và hàm apply_tx()
- Tạo state commitment (SHA-256/BLAKE2)

Tất cả module khác (block, consensus, network) **không được tự ý định nghĩa lại** encoding/hashing/signing.

---

## 2. Thành phần trong thư mục
core/
├─ encoding.py
├─ crypto_layer.py
├─ types_tx.py
└─ state.py


---

## 3. Nhiệm vụ từng file

### `encoding.py`
- Cung cấp `canonical_json(obj) -> bytes`
- Bảo đảm:
  - sort key
  - không space thừa
  - UTF-8 encoding
- Dùng cho mọi dữ liệu trước khi hash hoặc ký.

---

### `crypto_layer.py`
- Sinh keypair validator/participant
- Hàm ký:
  - `sign_struct(ctx, keypair, obj_dict)`
- Hàm verify:
  - `verify_struct(ctx, pubkey, obj_dict, signature)`
- Domain separation:
  - `TX:chain_id`
  - `HEADER:chain_id`
  - `VOTE:chain_id`
- Hàm hash:
  - `sha256(data)`
  - `sha256_hex(data)`

---

### `types_tx.py`
- `TxBody(sender_pubkey_hex, key, value)`
- `SignedTx`:
  - `.sign(keypair, key, value)`
  - `.verify()`
- Dữ liệu logic được ký **không** bao gồm signature.

---

### `state.py`
- State dạng `Dict[str, str]`
- `apply_tx(tx)`:
  - verify chữ ký
  - kiểm tra quyền sở hữu key
  - trả về state mới (immutable)
- `commitment()`:
  - SHA-256(canonical_json(state))

---

## 4. Trách nhiệm người phụ trách module
- Đảm bảo mọi encode/hash/sign đều deterministic.
- Đảm bảo transaction xử lý đúng quy tắc ownership.
- Đảm bảo state áp dụng tx giống nhau trên mọi node.

---

## 5. Cách test nhanh
pytest tests/test_core_crypto_state.py