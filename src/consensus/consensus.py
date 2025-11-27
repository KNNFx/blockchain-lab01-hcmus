from typing import Dict, List, Set, Callable, Optional
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consensus.vote import Vote, PHASE_PREVOTE, PHASE_PRECOMMIT, verify_vote, build_vote
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
        # Check đúng height/round
        if vote.height != self.height or vote.round != self.round:
            return False
        
        # Check chữ ký
        if not verify_vote(vote):
            return False
        
        # Check trùng lặp (một validator chỉ được vote 1 lần cho mỗi phase)
        validator = vote.validator_pubkey_hex
        block_hash = vote.block_hash
        
        if vote.phase == PHASE_PREVOTE:
            # Check xem đã prevote chưa
            for existing_votes in self.prevotes.values():
                if validator in existing_votes:
                    return False
            self.prevotes[block_hash].add(validator)
        
        elif vote.phase == PHASE_PRECOMMIT:
            # Check xem đã precommit chưa
            for existing_votes in self.precommits.values():
                if validator in existing_votes:
                    return False
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
    Consensus Engine, thực hiện quy trình 2-phase voting (Prevote + Precommit).
    Hỗ trợ:
    - Vote Buffering: Xử lý vote đến sớm/muộn.
    - Block Buffering: Xử lý block proposal đến sớm.
    - Fast Forward: Tự động catch-up nếu thấy tương lai đã chốt 1 block cao hơn.
    - Block Fetching: Yêu cầu block nếu bị thiếu.
    """
    def __init__(
        self, 
        validator_keypair,
        total_validators: int,
        validator_index: Optional[int] = None,
        on_finalize_callback: Optional[Callable] = None,
        on_ask_for_block: Optional[Callable] = None
    ):
        self.validator_keypair = validator_keypair
        self.total_validators = total_validators
        self.validator_index = validator_index  # Set during initialization
        self.on_finalize_callback = on_finalize_callback
        self.on_ask_for_block = on_ask_for_block
        
        #State
        self.current_height = 0
        self.current_round = 0
        
        #Storage
        self.vote_pools: Dict[tuple, VotePool] = {}
        self.proposed_blocks: Dict[str, dict] = {}  # block_hash -> block
        self.finalized_blocks: List[dict] = []
        
        #Buffer
        self.future_vote_buffer: Dict[tuple, List[Vote]] = defaultdict(list)
        self.future_block_buffer: Dict[int, dict] = {}
        self.waiting_for_block_to_finalize: Optional[tuple] = None # (height, block_hash)
        
        #Locking (Safety guarantee)
        self.locked_block: Optional[str] = None  # block_hash we're locked to
        self.locked_round: int = -1  # round where we locked
        self.valid_block: Optional[str] = None  # block with 2/3+ prevotes
        self.valid_round: int = -1  # round of valid block
        
        #Node's vote tracking
        self.my_prevote: Optional[str] = None
        self.my_precommit: Optional[str] = None
        
        #Block Layer (Mock)
        self.block_layer = MockBlockLayer()


    def on_receive_block(self, block) -> Optional[Vote]:
        """Xử lý khi nhận được block proposal. Trả về Vote nếu cần gửi."""
        block_hash = self._get_block_hash(block)
        height = self._get_block_height(block)
        
        #1. Block tương lai -> Thêm vào buffer
        if height > self.current_height:
            self.future_block_buffer[height] = block
            return None
            
        #2. Block quá khứ -> Bỏ qua
        if height < self.current_height:
            return None
        
        #3. Lưu block
        self.proposed_blocks[block_hash] = block
        
        #4. Check xem có đang chờ block này để finalize không
        waiting_vote = self._check_waiting_block(height, block_hash)
        if waiting_vote is not None:
            return waiting_vote

        #5. Nếu chưa prevote -> Validate và tạo Prevote
        if self.my_prevote is None:
            if self.block_layer.validate_block(block):
                # Prevote logic with locking consideration
                vote_for = None
                
                if self.locked_block is None:
                    # Not locked -> prevote this block
                    vote_for = block_hash
                elif self.locked_block == block_hash:
                    # Locked to this block -> prevote it
                    vote_for = block_hash
                elif self.valid_round >= self.locked_round:
                    # Valid block from higher round -> can unlock and prevote
                    vote_for = block_hash
                else:
                    # Locked to different block -> prevote nil
                    vote_for = "NIL"
                
                self.my_prevote = vote_for
                return build_vote(
                    height=self.current_height,
                    round=self.current_round,
                    block_hash=vote_for,
                    phase=PHASE_PREVOTE,
                    keypair=self.validator_keypair
                )
        
        return None
    
    def on_receive_vote(self, vote: Vote) -> Optional[Vote]:
        """Xử lý khi nhận được vote. Trả về Vote nếu cần gửi."""
        #1. Vote tương lai -> Buffer & Check Fast Forward
        if vote.height > self.current_height:
            self.future_vote_buffer[(vote.height, vote.round)].append(vote)
            if vote.height == self.current_height + 1:
                self._check_fast_forward(vote.height, vote.round)
            return None
            
        #2. Vote quá khứ -> Bỏ qua
        if vote.height < self.current_height:
            return None

        #3. Vote hiện tại -> Xử lý
        return self._process_vote_internal(vote)

    def _process_vote_internal(self, vote: Vote) -> Optional[Vote]:
        """Xử lý vote cho height/round hiện tại. Trả về Vote nếu cần gửi."""
        pool = self._get_vote_pool(vote.height, vote.round)
        
        if not pool.add_vote(vote):
            return None
         
        if vote.phase == PHASE_PREVOTE: #Nếu vote là prevote
            # Đủ 2/3 Prevote -> Update valid block & Lock & Gửi Precommit
            leader = pool.get_prevote_leader()
            if leader and leader != "NIL" and self.my_precommit is None:
                # Update valid block
                self.valid_block = leader
                self.valid_round = vote.round
                
                # Lock to this block (safety)
                self.locked_block = leader
                self.locked_round = vote.round
                
                # Send precommit
                self.my_precommit = leader
                return build_vote(
                    height=self.current_height,
                    round=self.current_round,
                    block_hash=leader,
                    phase=PHASE_PRECOMMIT,
                    keypair=self.validator_keypair
                )
        
        elif vote.phase == PHASE_PRECOMMIT: #Nếu vote là precommit
            # Đủ 2/3 Precommit -> Finalize
            leader = pool.get_precommit_leader()
            if leader and leader != "NIL":
                votes = self._finalize_block(leader, vote.height)
                # Return first vote if any (node_sim should handle list properly)
                return votes[0] if votes else None
        
        return None

    def _finalize_block(self, block_hash: str, height: int) -> List[Vote]:
        """Chốt block và chuyển sang height mới. Trả về votes cần broadcast."""
        block = self.proposed_blocks.get(block_hash)
        
        # Case: Thiếu block data -> Yêu cầu network gửi
        if not block:
            print(f"[WARN] Missing block {block_hash} for finalization! Requesting...")
            self.waiting_for_block_to_finalize = (height, block_hash)
            if self.on_ask_for_block:
                self.on_ask_for_block(block_hash)
            return []

        # Case: Đủ data -> Finalize
        self.finalized_blocks.append(block)
        print(f"- Block finalized at height {height}: {block_hash}")
        
        if self.on_finalize_callback:
            self.on_finalize_callback(block)
        
        # Reset state cho height mới và thu thập votes từ buffered blocks/votes
        return self._advance_to_next_height(height + 1)
        
    def should_propose(self, height: int, round: int = None) -> bool:
        """Kiểm tra quyền propose theo round-robin."""
        if round is None:
            round = self.current_round
        
        # Nếu không có validator_index, không propose
        if self.validator_index is None:
            return False
        
        # Round-robin: proposer_index = (height + round) % total_validators
        proposer_index = (height + round) % self.total_validators
        
        return self.validator_index == proposer_index
    
    def get_finalized_count(self) -> int:
        """Trả về số lượng block đã final"""
        return len(self.finalized_blocks)
    
    def get_latest_finalized(self):
        """Trả về block đã final gần nhất"""
        return self.finalized_blocks[-1] if self.finalized_blocks else None


    def _advance_to_next_height(self, new_height: int) -> List[Vote]:
        """Chuyển sang height tiếp theo và xử lý các buffer. Trả về danh sách votes cần broadcast."""
        self.current_height = new_height
        self.current_round = 0
        self.my_prevote = None
        self.my_precommit = None
        self.waiting_for_block_to_finalize = None
        
        # Reset locking state for new height
        self.locked_block = None
        self.locked_round = -1
        self.valid_block = None
        self.valid_round = -1
        
        votes_to_broadcast = []
        
        # 1. Xử lý Block Buffer (nếu có block chờ sẵn)
        if new_height in self.future_block_buffer:
            block = self.future_block_buffer.pop(new_height)
            vote = self.on_receive_block(block)
            if vote:
                votes_to_broadcast.append(vote)
            
        # 2. Xử lý Vote Buffer
        buffered_votes = self._process_buffered_votes(new_height, 0)
        if buffered_votes:
            votes_to_broadcast.extend(buffered_votes)
        
        return votes_to_broadcast

    def _check_waiting_block(self, height: int, block_hash: str) -> Optional[Vote]:
        """Kiểm tra xem block vừa nhận có phải là block đang chờ để finalize không."""
        if self.waiting_for_block_to_finalize:
            w_h, w_hash = self.waiting_for_block_to_finalize
            if w_h == height and w_hash == block_hash:
                print(f"Received missing block {block_hash}. Retrying finalization.")
                self.waiting_for_block_to_finalize = None
                votes = self._finalize_block(block_hash, height)
                # Return first vote if any
                return votes[0] if votes else None
        return None

    def _check_fast_forward(self, future_height: int, future_round: int):
        """
        Fast Forward: Nếu thấy block tương lai đã đồng thuận (2/3+ Precommit),
        thì finalize block hiện tại để đuổi theo.
        """
        if future_height != self.current_height + 1:
            return

        votes = self.future_vote_buffer.get((future_height, future_round), [])
        
        # Đếm số lượng precommit unique validators
        precommit_counts = defaultdict(int)
        voters = set()
        
        for v in votes:
            if v.phase == PHASE_PRECOMMIT and v.validator_pubkey_hex not in voters:
                precommit_counts[v.block_hash] += 1
                voters.add(v.validator_pubkey_hex)
        
        threshold = (2 * self.total_validators) // 3
        
        # Nếu bất kỳ block nào đạt supermajority
        for _, count in precommit_counts.items():
            if count > threshold:
                print(f"Fast Forward detected! Future height {future_height} has consensus.")
                
                # Tìm block hiện tại để finalize (Best effort)
                current_blk = self._find_proposal_for_height(self.current_height)
                if current_blk:
                    h = self._get_block_hash(current_blk)
                    print(f"Force finalizing current height {self.current_height} block {h}")
                    self._finalize_block(h, self.current_height)
                else:
                    print(f"Cannot Fast Forward: Missing block for current height {self.current_height}")
                    
                    future_blk = self.future_block_buffer.get(future_height)
                    if future_blk:
                        # Extract parent hash
                        parent_hash = None
                        # Check if it has header attribute
                        if hasattr(future_blk, 'header'):
                            # Check if header has parent_hash (Real Block)
                            if hasattr(future_blk.header, 'parent_hash'):
                                parent_hash = future_blk.header.parent_hash
                            # Check if MockBlock stores it differently
                            elif hasattr(future_blk, 'parent_hash'):
                                parent_hash = future_blk.parent_hash
                        
                        if parent_hash:
                            print(f"Found parent hash {parent_hash} from future block {future_height}. Requesting...")
                            self.waiting_for_block_to_finalize = (self.current_height, parent_hash)
                            if self.on_ask_for_block:
                                self.on_ask_for_block(parent_hash)
                return

    def _process_buffered_votes(self, height: int, round: int) -> List[Vote]:
        """Xử lý các vote đã buffer. Trả về danh sách votes cần broadcast."""
        votes_to_broadcast = []
        key = (height, round)
        if key in self.future_vote_buffer:
            votes = self.future_vote_buffer.pop(key)
            for v in votes:
                vote_response = self._process_vote_internal(v)
                if vote_response:
                    votes_to_broadcast.append(vote_response)
        return votes_to_broadcast
    
    def advance_round(self) -> List[Vote]:
        """Chuyển sang round tiếp theo (cho timeout/liveness). Trả về votes cần broadcast."""
        self.current_round += 1
        self.my_prevote = None
        self.my_precommit = None
        
        votes_to_broadcast = []
        
        # Process buffered votes for new round
        buffered_votes = self._process_buffered_votes(self.current_height, self.current_round)
        if buffered_votes:
            votes_to_broadcast.extend(buffered_votes)
        
        # Check if there's a buffered block for this height
        if self.current_height in self.future_block_buffer:
            block = self.future_block_buffer[self.current_height]
            vote = self.on_receive_block(block)
            if vote:
                votes_to_broadcast.append(vote)
        
        return votes_to_broadcast
    
    def set_validator_index(self, index: int):
        """Thiết lập index của validator (để proposer selection)."""
        self.validator_index = index

    def _get_vote_pool(self, height: int, round: int) -> VotePool:
        """Lấy pool vote"""
        key = (height, round)
        if key not in self.vote_pools:
            self.vote_pools[key] = VotePool(height, round, self.total_validators)
        return self.vote_pools[key]
    
    def _get_block_hash(self, block) -> str:
        return block.block_hash()
    
    def _get_block_height(self, block) -> int:
        return block.header.height
        
    def _find_proposal_for_height(self, height: int):
        """Tìm block proposal cho height"""
        for blk in self.proposed_blocks.values():
            if self._get_block_height(blk) == height:
                return blk
        return None
