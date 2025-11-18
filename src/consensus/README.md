# CONSENSUS MODULE – Prevote & Precommit Finality

## 1. Mục tiêu
Triển khai cơ chế đồng thuận hai pha:
- Prevote
- Precommit
- Finalize block khi đạt strict majority
- Đảm bảo Safety và Liveness

---

## 2. Thành phần thư mục
consensus/
├─ vote.py
└─ consensus.py


---

## 3. Nhiệm vụ từng file

### `vote.py`
- Struct:
  - `Vote(height, block_hash, phase, validator_pubkey_hex, signature)`
- Hàm:
  - `build_vote(keypair, height, block_hash, phase)`
  - `verify_vote(vote)`

---

### `consensus.py`
- Giữ vote pool cho từng height
- Hàm:
  - `on_proposed_block(block)`
  - `on_receive_vote(vote)`
  - Phát ra prevote / precommit khi đủ điều kiện
  - Phát hiện khi block đạt majority → finalize
- Callback:
  - `on_block_finalized(block_hash, height)`

---

## 4. Trách nhiệm người phụ trách module
- Đảm bảo tuyệt đối không thể finalize 2 block khác nhau cùng height.
- Luật prevote → precommit chính xác.
- Xác minh chữ ký vote bằng module core.

---

## 5. Test nhanh
pytest tests/test_consensus.py
