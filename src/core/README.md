# CORE MODULE – Crypto • Encoding • Transactions • State

## 1. Mục tiêu

Module này xây dựng toàn bộ phần “lõi” của blockchain:

- Deterministic encoding (canonical JSON)
- Chữ ký Ed25519/secp256k1 + domain separation
- Transaction struct (TxBody + SignedTx)
- State key–value và hàm apply_tx()
- State commitment (SHA-256/BLAKE2)

Các module khác phải sử dụng logic tại đây, **không tự viết lại**.

---

## 2. Cấu trúc files

core/
├─ encoding.py
├─ crypto_layer.py
├─ types_tx.py
└─ state.py

---

## 3. Mô tả từng file

### `encoding.py`

- Hàm: `canonical_json(obj) -> bytes`
- Yêu cầu:
  - sắp xếp key (sort_keys)
  - không thêm space
  - UTF-8
- Áp dụng cho hash/sign để đảm bảo deterministic.

### `crypto_layer.py`

- KeyPair (generate)
- sign_struct(ctx, keypair, obj)
- verify_struct(ctx, pubkey, obj, signature)
- Domain separation:
  - TX:chain_id
  - HEADER:chain_id
  - VOTE:chain_id
- SHA-256 / BLAKE2

### `types_tx.py`

- TxBody(sender_pubkey_hex, key, value)
- SignedTx(sign, verify)
- Không ký signature khi tạo payload để hash.

### `state.py`

- State dạng dict
- apply_tx(tx) → state mới
- Kiểm chữ ký + ownership rule
- commitment() → state_hash

---

## 4. Test module

pytest -v
