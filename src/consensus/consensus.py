from typing import Dict, List, Set, Callable, Optional
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consensus.vote import Vote, PHASE_PREVOTE, PHASE_PRECOMMIT, verify_vote
from mock.mock_block import MockBlockLayer


class VotePool:
    """
    Quản lý các phiếu bầu cho một (height, round) cụ thể.
    Theo dõi riêng biệt prevote và precommit.
    """
    def __init__(self, height: int, round: int, total_validators: int):
        self.height = height
        self.round = round
        self.total_validators = total_validators
        
        # Lưu vote theo phase -> block_hash -> set(validator_pubkey)
        self.prevotes: Dict[str, Set[str]] = defaultdict(set)
        self.precommits: Dict[str, Set[str]] = defaultdict(set)
        
        # Lưu lại toàn bộ object vote để debug nếu cần
        self.all_votes: List[Vote] = []
    
    def add_vote(self, vote: Vote) -> bool:
        """
        Thêm một vote vào pool.
        Trả về True nếu thêm thành công, False nếu lỗi hoặc trùng lặp.
        """
        # Check đúng height/round chưa
        if vote.height != self.height or vote.round != self.round:
            return False
        
        # Check chữ ký
        if not verify_vote(vote):
            return False
        
        # Check trùng lặp (một validator chỉ được vote 1 lần cho mỗi phase)
        validator = vote.validator_pubkey_hex
        block_hash = vote.block_hash
        
        if vote.phase == PHASE_PREVOTE:
            # Check xem ông này đã prevote chưa
            for existing_votes in self.prevotes.values():
                if validator in existing_votes:
                    return False  # Đã prevote rồi
            self.prevotes[block_hash].add(validator)
        
        elif vote.phase == PHASE_PRECOMMIT:
            # Check xem ông này đã precommit chưa
            for existing_votes in self.precommits.values():
                if validator in existing_votes:
                    return False  # Đã precommit rồi
            self.precommits[block_hash].add(validator)
        
        else:
            return False  # Phase không hợp lệ
        
        self.all_votes.append(vote)
        return True
    
    def get_prevote_count(self, block_hash: str) -> int:
        """Đếm số lượng prevote cho một block hash."""
        return len(self.prevotes.get(block_hash, set()))
    
    def get_precommit_count(self, block_hash: str) -> int:
        """Đếm số lượng precommit cho một block hash."""
        return len(self.precommits.get(block_hash, set()))
    
    def has_supermajority_prevotes(self, block_hash: str) -> bool:
        """Kiểm tra xem block có đạt 2/3+ prevote không."""
        count = self.get_prevote_count(block_hash)
        return count > (2 * self.total_validators // 3)
    
    def has_supermajority_precommits(self, block_hash: str) -> bool:
        """Kiểm tra xem block có đạt 2/3+ precommit không."""
        count = self.get_precommit_count(block_hash)
        return count > (2 * self.total_validators // 3)
    
    def get_prevote_leader(self) -> Optional[str]:
        """
        Trả về block_hash có nhiều prevote nhất nếu đạt supermajority.
        Nếu không ai đạt thì trả về None.
        """
        for block_hash, voters in self.prevotes.items():
            if self.has_supermajority_prevotes(block_hash):
                return block_hash
        return None
    
    def get_precommit_leader(self) -> Optional[str]:
        """
        Trả về block_hash có nhiều precommit nhất nếu đạt supermajority.
        Nếu không ai đạt thì trả về None.
        """
        for block_hash, voters in self.precommits.items():
            if self.has_supermajority_precommits(block_hash):
                return block_hash
        return None


class ConsensusEngine:
    """
    Engine đồng thuận chính, thực hiện quy trình 2-phase voting (Prevote + Precommit).
    
    Luồng xử lý:
    1. Nhận block proposal
    2. Nếu hợp lệ -> gửi PREVOTE
    3. Nếu nhận đủ 2/3+ prevote cho cùng 1 block -> gửi PRECOMMIT
    4. Nếu nhận đủ 2/3+ precommit cho cùng 1 block -> FINALIZE
    """
    def __init__(
        self, 
        validator_keypair,
        total_validators: int,
        on_finalize_callback: Optional[Callable] = None
    ):
        self.validator_keypair = validator_keypair
        self.total_validators = total_validators
        self.on_finalize_callback = on_finalize_callback
        
        # Trạng thái hiện tại
        self.current_height = 0
        self.current_round = 0
        
        # Kho chứa vote cho từng (height, round)
        self.vote_pools: Dict[tuple, VotePool] = {}
        
        # Theo dõi xem mình đã vote cái gì chưa
        self.my_prevote: Optional[str] = None  # block_hash mình đã prevote
        self.my_precommit: Optional[str] = None  # block_hash mình đã precommit
        
        # Các block được đề xuất mà mình đã nhận
        self.proposed_blocks: Dict[str, dict] = {}  # block_hash -> block
        
        # Các block đã finalize
        self.finalized_blocks: List[dict] = []

        # Block Layer (Mock) để validate block
        self.block_layer = MockBlockLayer()
    
    def _get_vote_pool(self, height: int, round: int) -> VotePool:
        """Lấy hoặc tạo mới vote pool cho height/round cụ thể."""
        key = (height, round)
        if key not in self.vote_pools:
            self.vote_pools[key] = VotePool(height, round, self.total_validators)
        return self.vote_pools[key]
    
    def _get_block_hash(self, block) -> str:
        """Lấy hash của block (hỗ trợ cả dict và object Block)."""
        if isinstance(block, dict):
            return block.get("hash", "")
        else:
            # Dành cho object Block thật (khi blocklayer sẵn sàng)
            return block.compute_hash() if hasattr(block, "compute_hash") else str(block)
    
    def _get_block_height(self, block) -> int:
        """Lấy height của block."""
        if isinstance(block, dict):
            return block.get("height", 0)
        else:
            return block.header.height if hasattr(block, "header") else 0
    
    def on_receive_block(self, block) -> bool:
        """
        Được gọi khi nhận được một block proposal.
        
        Nếu block valid và mình chưa prevote -> gửi PREVOTE.
        Trả về True nếu mình đã prevote, False nếu không.
        """
        block_hash = self._get_block_hash(block)
        height = self._get_block_height(block)
        
        # Lưu block lại
        self.proposed_blocks[block_hash] = block
        
        # Cập nhật height nếu thấy block mới cao hơn
        if height > self.current_height:
            self.current_height = height
            self.current_round = 0
            self.my_prevote = None
            self.my_precommit = None
        
        # Nếu mình đã prevote rồi thì thôi, không vote lại
        if self.my_prevote is not None:
            return False
        
        # Validate block sử dụng MockBlockLayer
        is_valid = self.block_layer.validate_block(block)
        
        if is_valid:
            # Gửi prevote
            self.my_prevote = block_hash
            return True
        
        return False
    
    def on_receive_vote(self, vote: Vote) -> Optional[str]:
        """
        Được gọi khi nhận được vote từ validator khác.
        
        Trả về:
        - "PREVOTE_READY": nếu block đạt 2/3+ prevote -> gửi precommit
        - "FINALIZE": nếu block đạt 2/3+ precommit -> finalize block
        - None: chưa có gì đặc biệt
        """
        # Lấy pool tương ứng
        pool = self._get_vote_pool(vote.height, vote.round)
        
        # Thêm vote vào pool
        if not pool.add_vote(vote):
            return None  # Vote lỗi hoặc trùng
        
        # Check xem có chuyển trạng thái được không
        if vote.phase == PHASE_PREVOTE:
            prevote_leader = pool.get_prevote_leader()
            if prevote_leader and self.my_precommit is None:
                # Đã đủ 2/3+ prevote -> gửi precommit
                self.my_precommit = prevote_leader
                return "PREVOTE_READY"
        
        elif vote.phase == PHASE_PRECOMMIT:
            precommit_leader = pool.get_precommit_leader()
            if precommit_leader:
                # Đã đủ 2/3+ precommit -> finalize luôn!
                self._finalize_block(precommit_leader, vote.height)
                return "FINALIZE"
        
        return None
    
    def _finalize_block(self, block_hash: str, height: int):
        """
        Finalize block khi đã đủ 2/3+ precommit.
        """
        block = self.proposed_blocks.get(block_hash)
        if not block:
            print(f"Cảnh báo: Finalize block lạ {block_hash}")
            return
        
        self.finalized_blocks.append(block)
        print(f"- Block đã finalize tại height {height}: {block_hash}")
        
        # Gọi callback nếu có
        if self.on_finalize_callback:
            self.on_finalize_callback(block)
        
        # Nhảy sang height tiếp theo
        self.current_height = height + 1
        self.current_round = 0
        self.my_prevote = None
        self.my_precommit = None
    
    def should_propose(self, height: int) -> bool:
        """
        Kiểm tra xem mình có được quyền propose block ở height này không.
        """
        # Đơn giản hóa: validator 0 propose height 0, validator 1 propose height 1...
        # Thực tế cần thuật toán chọn leader xịn hơn
        return True
    
    def get_finalized_count(self) -> int:
        """Trả về số lượng block đã finalize."""
        return len(self.finalized_blocks)
    
    def get_latest_finalized(self):
        """Trả về block finalize mới nhất, hoặc None."""
        return self.finalized_blocks[-1] if self.finalized_blocks else None
