import sys
import os
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.consensus.consensus import ConsensusEngine, VotePool, PHASE_PREVOTE, PHASE_PRECOMMIT
from src.consensus.vote import Vote, KeyPair, build_vote, verify_vote

@dataclass
class MockBlockHeader:
    height: int

class MockBlock:
    def __init__(self, hash_val: str, height: int):
        self.header = MockBlockHeader(height=height)
import sys
import os
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.consensus.consensus import ConsensusEngine, VotePool, PHASE_PREVOTE, PHASE_PRECOMMIT
from src.consensus.vote import Vote, KeyPair, build_vote, verify_vote

@dataclass
class MockBlockHeader:
    height: int

class MockBlock:
    def __init__(self, hash_val: str, height: int):
        self.header = MockBlockHeader(height=height)
        self._hash = hash_val
    
    def block_hash(self) -> str:
        return self._hash

def test_vote_mechanics():
    """Test tạo và xác thực phiếu bầu (vote)."""
    keypair = KeyPair()
    
    # 1. Tạo một vote hợp lệ
    vote = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, keypair)
    
    # 2. Xác thực vote hợp lệ
    assert verify_vote(vote) is True
    assert vote.height == 1
    assert vote.round == 0
    assert vote.block_hash == "block_hash_1"
    assert vote.phase == PHASE_PREVOTE
    assert vote.validator_pubkey_hex == keypair.pubkey()
    
    # 3. Giả mạo vote (chữ ký không khớp)
    vote.block_hash = "tampered_hash"
    assert verify_vote(vote) is False

def test_vote_pool():
    """Test logic của VotePool: thêm vote, check trùng lặp, và đếm supermajority."""
    total_validators = 4
    pool = VotePool(height=1, round=0, total_validators=total_validators)
    
    keypairs = [KeyPair() for _ in range(total_validators)]
    
    # 1. Thêm vote hợp lệ
    vote1 = build_vote(1, 0, "block_A", PHASE_PREVOTE, keypairs[0])
    assert pool.add_vote(vote1) is True
    assert pool.get_prevote_count("block_A") == 1
    
    # 2. Thêm vote trùng lặp (cùng validator, cùng phase) -> fail
    vote1_dup = build_vote(1, 0, "block_A", PHASE_PREVOTE, keypairs[0])
    assert pool.add_vote(vote1_dup) is False
    assert pool.get_prevote_count("block_A") == 1
    
    # 3. Thêm vote cho block khác
    vote2 = build_vote(1, 0, "block_B", PHASE_PREVOTE, keypairs[1])
    assert pool.add_vote(vote2) is True
    assert pool.get_prevote_count("block_B") == 1
    
    # 4. Check supermajority (Cần > 2/3 của 4 là 3 votes)
    assert pool.has_supermajority_prevotes("block_A") is False
    
    # Thêm 2 vote nữa cho block_A
    vote3 = build_vote(1, 0, "block_A", PHASE_PREVOTE, keypairs[2])
    vote4 = build_vote(1, 0, "block_A", PHASE_PREVOTE, keypairs[3])
    pool.add_vote(vote3)
    pool.add_vote(vote4)
    
    assert pool.get_prevote_count("block_A") == 3
    assert pool.has_supermajority_prevotes("block_A") is True
    assert pool.get_prevote_leader() == "block_A"

def test_consensus_engine_unit():
    """Test từng method riêng lẻ của ConsensusEngine."""
    keypair = KeyPair()
    engine = ConsensusEngine(validator_keypair=keypair, total_validators=4)
    
    # 1. Test on_receive_block
    block = MockBlock(hash_val="block_1", height=1)
    
    # Engine vote PREVOTE
    assert engine.on_receive_block(block) is True
    assert engine.my_prevote == "block_1"
    
    # Engine không vote lại cho cùng height/round
    assert engine.on_receive_block(block) is False
    
    # 2. Test on_receive_vote (Chuyển đổi trạng thái)
    # Reset engine
    engine = ConsensusEngine(validator_keypair=keypair, total_validators=4)
    other_keypairs = [KeyPair() for _ in range(3)]
    
    # Thêm 3 PREVOTE cho block_1
    # Vote 1
    v1 = build_vote(1, 0, "block_1", PHASE_PREVOTE, other_keypairs[0])
    assert engine.on_receive_vote(v1) is None
    
    # Vote 2
    v2 = build_vote(1, 0, "block_1", PHASE_PREVOTE, other_keypairs[1])
    assert engine.on_receive_vote(v2) is None
    
    # Vote 3 -> PREVOTE_READY
    v3 = build_vote(1, 0, "block_1", PHASE_PREVOTE, other_keypairs[2])
    assert engine.on_receive_vote(v3) == "PREVOTE_READY"
    assert engine.my_precommit == "block_1"

def test_consensus_engine_flow():
    """
    Test luồng hoạt động của ConsensusEngine.
    Mô phỏng quy trình từ nhận block -> prevote -> precommit -> finalize.
    """
    # 1. Setup
    total_validators = 4
    keypair = KeyPair()
    mock_finalize = MagicMock() # Thực tế thay MagicMock() bằng hàm thêm block vào ledge
    
    engine = ConsensusEngine(
        validator_keypair=keypair,
        total_validators=total_validators,
        on_finalize_callback=mock_finalize
    )
    
    # 2. Nhận Block Proposal
    block = MockBlock(hash_val="block_hash_1", height=1)
    
    did_prevote = engine.on_receive_block(block)
    assert did_prevote is True
    assert engine.my_prevote == "block_hash_1"
    
    # 3. Mô phỏng nhận PREVOTE từ các validator khác
    other_keypairs = [KeyPair() for _ in range(total_validators - 1)]
    
    # Vote 1 (Của mình - tự nạp lại)
    vote1 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, keypair)
    engine.on_receive_vote(vote1)
    
    # Vote 2
    vote2 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, other_keypairs[0])
    engine.on_receive_vote(vote2)
    
    # Vote 3 (Kích hoạt PRECOMMIT)
    vote3 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, other_keypairs[1])
    action = engine.on_receive_vote(vote3)
    
    assert action == "PREVOTE_READY"
    assert engine.my_precommit == "block_hash_1"
    
    # 4. Mô phỏng nhận PRECOMMIT
    # Vote 1 (Của mình)
    commit1 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, keypair)
    engine.on_receive_vote(commit1)
    
    # Vote 2
    commit2 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, other_keypairs[0])
    engine.on_receive_vote(commit2)
    
    # Vote 3 (Kích hoạt FINALIZE)
    commit3 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, other_keypairs[1])
    action = engine.on_receive_vote(commit3)
    
    assert action == "FINALIZE"
    assert engine.get_finalized_count() == 1
    finalized_block = engine.get_latest_finalized()
    assert finalized_block.block_hash() == "block_hash_1"
    
    # Kiểm tra xem callback đã được gọi chưa
    mock_finalize.assert_called_once_with(block)

if __name__ == "__main__":
    pytest.main([__file__])
