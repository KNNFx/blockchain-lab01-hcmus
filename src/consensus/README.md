# Consensus Module - BFT Simplified

Module này chịu trách nhiệm đảm bảo sự đồng thuận (Consensus) giữa các node trong mạng lưới Blockchain, đảm bảo tính **Safety** (không có 2 block khác nhau cùng height) và **Liveness** (không có node nào bị mắc kẹt trong quá trình consensus).

---

## 1. Tiêu chuẩn & Giao thức

Module này được xây dựng dựa trên phiên bản đơn giản hóa của giao thức **PBFT (Practical Byzantine Fault Tolerance)** và **Tendermint BFT**.
*   **Mô hình**: State Machine Replication.
*   **Safety**: Đảm bảo bởi cơ chế Locking (2/3+ Prevotes).
*   **Liveness**: Đảm bảo bởi cơ chế Timeout và Round-Robin Proposer.

---

## 2. Cấu trúc files

consensus/
├─ consensus.py
├─ vote.py
└─ README.md

*   `consensus.py`: Mã nguồn chính của Consensus Engine, chứa logic xử lý vote, block và state machine.
*   `vote.py`: Định nghĩa cấu trúc `Vote`, các phase (`PREVOTE`, `PRECOMMIT`) và logic ký/xác thực chữ ký điện tử.
*   `README.md`: Tài liệu hướng dẫn chi tiết về module.

---

## 3. Các hàm chính

### `ConsensusEngine`
Class chính điều phối toàn bộ quá trình.

*   **`__init__(...)`**: Khởi tạo engine.
    *   `validator_keypair`: KeyPair dùng để ký vote.
    *   `total_validators`: Tổng số validator trong mạng.
    *   `validator_index`: Index của validator hiện tại (dùng cho Proposer Selection).
    *   `on_finalize_callback`: Callback khi block được chốt.
    *   `on_ask_for_block`: Callback khi cần xin block từ mạng.

*   **`on_receive_block(block) -> Optional[Vote]`**
    *   Được gọi khi Node nhận được một Block Proposal.
    *   **Xử lý**:
        1.  Kiểm tra hợp lệ (Block Layer).
        2.  Kiểm tra **Locking Rules** (mục Safety).
        3.  Nếu hợp lệ và an toàn -> Tạo và trả về **PREVOTE**.
    *   **Return**: Trả về object `Vote` (Prevote) để node gửi đi, hoặc `None`.

*   **`on_receive_vote(vote) -> Optional[Vote]`**
    *   Được gọi khi Node nhận được một Vote.
    *   **Xử lý**:
        1.  Thêm vote vào `VotePool`.
        2.  Kiểm tra ngưỡng 2/3 (Supermajority).
        3.  Nếu đủ 2/3 Prevote -> Lock & Trả về **PRECOMMIT**.
        4.  Nếu đủ 2/3 Precommit -> **FINALIZE** block.
    *   **Return**: Trả về object `Vote` (Precommit) để node gửi đi, hoặc `None`.

*   **`advance_round() -> List[Vote]`**
    *   Được gọi khi Timeout (không nhận được proposal hoặc consensus quá lâu).
    *   **Xử lý**: Tăng `current_round`, reset trạng thái vote của round cũ, xử lý các vote/block đã buffer cho round mới.
    *   **Return**: Danh sách các `Vote` cần gửi đi trong round mới.

*   **`should_propose(height, round) -> bool`**
    *   Kiểm tra xem validator hiện tại có phải là Proposer cho (height, round) này không.
    *   **Logic**: Round-Robin dựa trên `validator_index`.

---

## 4. Quy trình hoạt động (Workflow)

### Normal Case (Mạng tốt)
1.  **Propose**: Proposer (được chọn theo Round-Robin) tạo Block và gửi cho mạng.
2.  **Prevote**:
    *   Validator nhận Block.
    *   Nếu Block hợp lệ và không vi phạm Lock -> Gửi **PREVOTE**.
3.  **Precommit**:
    *   Validator thu thập đủ 2/3 Prevote cho một Block.
    *   Validator **Lock** vào Block đó -> Gửi **PRECOMMIT**.
4.  **Finalize**:
    *   Validator thu thập đủ 2/3 Precommit.
    *   Validator **Commit** (Finalize) Block -> Chuyển sang Height tiếp theo.

### Timeout (Liveness)
Nếu Proposer bị offline hoặc mạng chậm:
1.  Node chờ một khoảng thời gian (Timeout).
2.  Gọi `advance_round()`.
3.  Chuyển sang Round mới (`current_round + 1`).
4.  Proposer mới (được tính lại theo round mới) sẽ đề xuất block.

---

## 5. Cơ chế An toàn (Safety & Locking)

Để đảm bảo không bao giờ có 2 block khác nhau được finalize tại cùng một height (Fork), hệ thống sử dụng cơ chế **Locking**:

*   **`locked_block`**: Block mà validator đã gửi Precommit.
*   **`locked_round`**: Round mà validator đã lock.
*   **`valid_block`**: Block gần nhất đạt được 2/3 Prevote.
*   **`valid_round`**: Round của valid_block.

**Luật Locking (trong `on_receive_block`):**
*   Nếu `locked_block` là `None`: Có thể Prevote cho block mới.
*   Nếu `locked_block` trùng với block nhận được: Có thể Prevote lại.
*   Nếu `locked_block` KHÁC block nhận được:
    *   Chỉ được phép "Unlock" và Prevote cho block mới NẾU block mới có `valid_round` > `locked_round` (tức là đã có bằng chứng 2/3 Prevote ở round cao hơn).
    *   Ngược lại: Phải Prevote **NIL** (từ chối block).

---

## 6. Xử lý các tình huống mạng (Robustness)

### A. Vote đến sớm (Future Vote)
*   **Code**: Hàm `on_receive_vote` kiểm tra `vote.height > current_height`.
*   **Xử lý**: Lưu vào `future_vote_buffer`. Nếu là vote của `current_height + 1`, kích hoạt kiểm tra **Fast Forward**.

### B. Block đến sớm (Future Block)
*   **Code**: Hàm `on_receive_block` kiểm tra `height > current_height`.
*   **Xử lý**: Lưu vào `future_block_buffer`. Tự động xử lý khi node chuyển sang height đó.

### C. Mất gói tin Finalize (Fast Forward)
*   **Cơ chế**: Nếu nhận thấy block tương lai (`current_height + 1`) đã có đủ 2/3 Precommit, node hiểu rằng mình đã bị lỡ nhịp.
*   **Hành động**: Tự động Finalize block hiện tại (ngay cả khi chưa đủ vote cục bộ) để đuổi theo mạng.

### D. Thiếu Block (Block Fetching)

Hệ thống xử lý 2 trường hợp thiếu block:

**1. Thiếu Block Data (Đã biết Hash)**
*   **Tình huống**: Node nhận đủ 2/3 Precommit cho một block hash cụ thể, nhưng chưa nhận được nội dung block đó.
*   **Hành động**:
    1.  Lưu trạng thái đang chờ vào `waiting_for_block_to_finalize`.
    2.  Gọi callback `on_ask_for_block(block_hash)` để yêu cầu mạng gửi lại.
    3.  Khi Block về (qua `on_receive_block`), node sẽ tự động resume quá trình Finalize.

**2. Thiếu Block Hash (Chưa biết Hash - Fast Forward)**
*   **Tình huống**: Node phát hiện Fast Forward (tương lai đã chốt), nhưng node không biết block của height hiện tại là gì (do chưa nhận được proposal).
*   **Hành động**:
    1.  Node tìm **Block Tương Lai** (block kích hoạt Fast Forward) trong `future_block_buffer`.
    2.  Nếu có Block Tương Lai: Lấy `parent_hash` từ block đó (chính là hash của block hiện tại). -> Quay về trường hợp 1.
    3.  Nếu chưa có Block Tương Lai: Node buộc phải **CHỜ** cho đến khi nhận được Block Tương Lai (để có thông tin về quá khứ).

---

## 7. Testing

Module đi kèm với bộ test toàn diện trong `tests/test_consensus.py`.

**Chạy tests:**
```bash
# Chạy tất cả tests
python -m pytest tests/test_consensus.py -v

# Chạy một test cụ thể, ví dụ như test_locking_safety
python -m pytest tests/test_consensus.py::test_locking_safety -v
```

---


## 8. Troubleshooting

### Vấn đề: Node không tiến tới Precommit phase
*   **Nguyên nhân**: Không đủ 2/3 Prevotes.
*   **Giải pháp**: Kiểm tra xem tất cả validators có nhận được block không. Kiểm tra network connectivity.

### Vấn đề: Node bị stuck ở một round
*   **Nguyên nhân**: Timeout không được trigger hoặc `advance_round()` không được gọi.
*   **Giải pháp**: Đảm bảo node_sim implement timeout timer đúng cách.

### Vấn đề: Double finalization (2 blocks cùng height)
*   **Nguyên nhân**: Locking mechanism bị bypass hoặc bug trong logic.
*   **Giải pháp**: Kiểm tra log của `on_receive_block` để đảm bảo locking rules được áp dụng. Chạy `test_locking_safety` để verify.

### Vấn đề: Node tụt hậu và không bắt kịp
*   **Nguyên nhân**: Node_sim không implement state sync cho khoảng cách 2+ heights.
*   **Giải pháp**: Implement batch block fetching như mô tả trong section 10.5.

---

## 9. Hướng dẫn Tích hợp & Mở rộng

### Cách tích hợp vào Node
Ví dụ và hướng dẫn sử dụng module này trong một Blockchain Node thực tế:

1.  **Khởi tạo**:
    ```python
    engine = ConsensusEngine(
        validator_keypair=my_keypair,
        total_validators=4,
        validator_index=0,
        on_finalize_callback=self.save_block_to_db,
        on_ask_for_block=self.broadcast_get_block
    )
    ```

2.  **Kết nối Network**:
    *   Khi nhận message `BLOCK`: Gọi `engine.on_receive_block(block)`.
    *   Khi nhận message `VOTE`: Gọi `engine.on_receive_vote(vote)`.
    *   **Quan trọng**: Các hàm này trả về `Vote` object hoặc `List[Vote]`. Bạn cần serialize và gửi vote này tới tất cả peers ngay lập tức.
    *   **Lưu ý**: Network layer chỉ có method `send(msg, now)` để gửi message 1-1. Node_sim cần implement broadcast bằng cách loop qua tất cả peers.

    **Ví dụ xử lý Block:**
    ```python
    def handle_block_message(self, block):
        vote = self.consensus_engine.on_receive_block(block)
        if vote:
            # Broadcast vote ra mạng (gửi tới tất cả peers)
            for peer_id in self.peer_list:
                msg = self.create_vote_message(vote, peer_id)
                self.network.send(msg, self.current_time)
    ```

    **Ví dụ xử lý Vote:**
    ```python
    def handle_vote_message(self, vote):
        result_vote = self.consensus_engine.on_receive_vote(vote)
        if result_vote:
            # Có thể là Precommit vote, broadcast tới tất cả peers
            for peer_id in self.peer_list:
                msg = self.create_vote_message(result_vote, peer_id)
                self.network.send(msg, self.current_time)
    ```

3.  **Timeout & Round Management**:
    *   Node cần implement một timer để detect timeout.
    *   Timeout nên được trigger khi:
        *   Không nhận được proposal trong một khoảng thời gian (ví dụ: 5 giây).
        *   Không đủ vote để tiến tới Precommit phase (ví dụ: 10 giây).
    
    **Ví dụ:**
    ```python
    # Trong node_sim hoặc network layer
    def start_round_timer(self):
        self.timeout = 5.0  # seconds
        self.timer = Timer(self.timeout, self.on_round_timeout)
        self.timer.start()
    
    def on_round_timeout(self):
        # Gọi advance_round và broadcast các vote mới
        votes = self.consensus_engine.advance_round()
        for vote in votes:
            for peer_id in self.peer_list:
                msg = self.create_vote_message(vote, peer_id)
                self.network.send(msg, self.current_time)
        # Reset timer cho round mới
        self.start_round_timer()
    ```

4.  **Proposer Logic**:
    *   Nếu node là Proposer, cần tạo và gửi Block Proposal.
    
    **Ví dụ:**
    ```python
    def maybe_propose(self):
        height = self.consensus_engine.current_height
        round = self.consensus_engine.current_round
        
        if self.consensus_engine.should_propose(height, round):
            # Tạo block mới
            block = self.create_new_block()
            # Broadcast block tới tất cả peers
            for peer_id in self.peer_list:
                msg = self.create_block_message(block, peer_id)
                self.network.send(msg, self.current_time)
    ```

5.  **State Synchronization (Node tụt hậu 2+ heights)**:
    *   Consensus module chỉ buffer block/vote của `current_height + 1`.
    *   Nếu node phát hiện mình tụt hậu xa hơn (nhận block/vote của `current_height + 2` trở lên), node_sim cần implement cơ chế sync:
        *   Broadcast status heartbeat (height hiện tại).
        *   Lắng nghe status từ các node khác.
        *   Nếu phát hiện tụt hậu nhiều, request batch blocks từ peers.
        *   Áp dụng các block thiếu lên ledger trước khi resume consensus.
    
    **Ví dụ phát hiện tụt hậu:**
    ```python
    def handle_block_message(self, block):
        if block.height > self.consensus_engine.current_height + 1:
            # Tụt hậu quá xa, cần sync
            self.request_missing_blocks(
                from_height=self.consensus_engine.current_height,
                to_height=block.height - 1
            )
        else:
            # Xử lý bình thường
            vote = self.consensus_engine.on_receive_block(block)
            if vote:
                # Broadcast vote tới tất cả peers
                for peer_id in self.peer_list:
                    msg = self.create_vote_message(vote, peer_id)
                    self.network.send(msg, self.current_time)
    ```

### Công việc của các module khác (Integration Points)

Các phần sau đây cần được implement bởi các module/người khác để hoàn thiện hệ thống:

*   **Ledger** (`src/blocklayer/ledger.py`):
    *   Implement hàm để gán cho `on_finalize_callback`.
    *   Hàm này sẽ lưu block vào ledger khi consensus finalize.

*   **Network Layer** (`src/network/`):
    *   Implement hàm để gán cho `on_ask_for_block`.
    *   Hàm này gửi message `GET_BLOCK` qua P2P network để yêu cầu block từ peers.

*   **Node Simulator** (`src/node_sim/`):
    *   Implement timeout timer cho round advancement (gọi `advance_round()`).
    *   Implement state synchronization khi node tụt hậu 2+ heights.
    *   **Implement broadcast logic**: Loop qua tất cả peers và dùng `network.send()` để gửi votes/blocks.
    *   Implement proposer logic (tạo và gửi block proposals khi `should_propose()` trả về True).
    *   Wire callbacks từ network messages đến consensus engine methods.
    *   Implement block request/response protocol (GET_BLOCK messages) cho `on_ask_for_block` callback.
