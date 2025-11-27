# CONSENSUS MODULE – Prevote • Precommit • Finality

## 1. Mục tiêu
Triển khai thuật toán đồng thuận 2-phase (dựa trên PBFT/Tendermint) để đảm bảo tính nhất quán (Safety) và khả năng hoạt động (Liveness) của mạng lưới blockchain.

Quy trình đồng thuận gồm 3 bước chính:
1.  **Propose**: Validator nhận Block mới.
2.  **Prevote**: Validator bỏ phiếu xác nhận Block (Phase 1).
3.  **Precommit**: Khi đủ 2/3 số phiếu Prevote, Validator chuyển sang bỏ phiếu cam kết (Phase 2).
4.  **Finalize**: Khi đủ 2/3 số phiếu Precommit, Block được coi là hoàn tất và được ghi vào Ledger.

---

## 2. Cấu trúc thư mục
```
consensus/
├─ vote.py
└─ consensus.py


---

## 3. File chi tiết

### `vote.py`
- Vote struct:
  - height
  - round
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

python -m pytest tests/test_consensus.py

Test bao gồm:
*   `test_vote_mechanics`: Kiểm tra tạo và xác thực chữ ký phiếu bầu.
*   `test_vote_pool`: Kiểm tra logic đếm phiếu và chặn phiếu trùng lặp.
*   `test_consensus_engine_unit`: Kiểm tra từng hàm riêng lẻ.
*   `test_consensus_engine_flow`: Mô phỏng toàn bộ quy trình từ nhận block đến finalize.