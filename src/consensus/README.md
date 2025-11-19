# CONSENSUS MODULE – Prevote • Precommit • Finality

## 1. Mục tiêu
Triển khai đồng thuận 2-phase như yêu cầu:
- Prevote
- Precommit
- Finalize block khi đạt strict majority
- Bảo đảm Safety & Liveness

---

## 2. Cấu trúc thư mục
consensus/
├─ vote.py
└─ consensus.py


---

## 3. File chi tiết

### `vote.py`
- Vote struct:
  - height
  - block_hash
  - phase (PREVOTE / PRECOMMIT)
  - validator_pubkey_hex
  - signature
- build_vote()
- verify_vote()

### `consensus.py`
- VotePool cho từng height
- on_receive_block()
- on_receive_vote()
- Điều kiện phát prevote → precommit
- Điều kiện finalize block
- Callback: on_block_finalized()

---

## 4. Test module
pytest tests/test_consensus.py