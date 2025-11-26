"""
Bộ test cho module blocklayer - Block, BlockHeader, Validation, và Ledger
"""

import sys
from pathlib import Path

# Thêm src vào path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from core import KeyPair, TxBody, SignedTx, State
from blocklayer import BlockHeader, Block, build_block, validate_block, Ledger


def test_build_genesis_block():
    """Test tạo genesis block (block đầu tiên không có parent)"""
    kp = KeyPair()
    state = State()
    txs = []
    
    block = build_block(None, state, txs, kp)
    
    assert block.header.height == 0
    assert block.header.parent_hash == "0" * 64
    assert block.header.proposer_pubkey_hex == kp.pubkey()
    assert len(block.txs) == 0


def test_build_block_with_transactions():
    """Test tạo block với transactions"""
    proposer = KeyPair()
    alice = KeyPair()
    bob = KeyPair()
    
    # Tạo genesis block
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    # Tạo transactions với key riêng cho mỗi user
    tx1 = SignedTx.create(TxBody(alice.pubkey(), "balance", 100), alice)
    tx2 = SignedTx.create(TxBody(bob.pubkey(), "name", "Bob"), bob)
    
    # Tạo block với transactions
    block = build_block(genesis, genesis_state, [tx1, tx2], proposer)
    
    assert block.header.height == 1
    assert block.header.parent_hash == genesis.block_hash()
    assert len(block.txs) == 2
    
    # Xác thực state đã được cập nhật đúng
    new_state = genesis_state.copy()
    for tx in block.txs:
        new_state.apply_tx(tx)
    
    assert new_state.get(alice.pubkey(), "balance") == 100
    assert new_state.get(bob.pubkey(), "name") == "Bob"


def test_validate_genesis_block():
    """Test validate genesis block"""
    kp = KeyPair()
    state = State()
    
    block = build_block(None, state, [], kp)
    
    assert validate_block(block, None, state) is True


def test_validate_block_valid():
    """Test validate một block hợp lệ"""
    proposer = KeyPair()
    alice = KeyPair()
    
    # Genesis
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    # Block 1
    tx1 = SignedTx.create(TxBody(alice.pubkey(), "msg", "hello"), alice)
    block1 = build_block(genesis, genesis_state, [tx1], proposer)
    
    assert validate_block(block1, genesis, genesis_state) is True


def test_validate_block_wrong_height():
    """Test validation thất bại khi height sai"""
    proposer = KeyPair()
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    # Tạo block với height sai
    block = build_block(genesis, genesis_state, [], proposer)
    block.header.height = 5  # Height sai
    
    assert validate_block(block, genesis, genesis_state) is False


def test_validate_block_wrong_parent_hash():
    """Test validation thất bại khi parent hash sai"""
    proposer = KeyPair()
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    # Tạo block với parent hash sai
    block = build_block(genesis, genesis_state, [], proposer)
    block.header.parent_hash = "0" * 64  # Parent hash sai
    
    assert validate_block(block, genesis, genesis_state) is False


def test_validate_block_wrong_state_hash():
    """Test validation thất bại khi state hash sai"""
    proposer = KeyPair()
    alice = KeyPair()
    
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    tx1 = SignedTx.create(TxBody(alice.pubkey(), "msg", "hello"), alice)
    block = build_block(genesis, genesis_state, [tx1], proposer)
    
    # Thay đổi state hash
    block.header.state_hash = "0" * 64
    
    assert validate_block(block, genesis, genesis_state) is False


def test_validate_block_invalid_signature():
    """Test validation thất bại khi chữ ký header không hợp lệ"""
    proposer = KeyPair()
    faker = KeyPair()
    
    genesis_state = State()
    genesis = build_block(None, genesis_state, [], proposer)
    
    block = build_block(genesis, genesis_state, [], proposer)
    
    # Thay đổi chữ ký
    block.header_signature = "0" * 128
    
    assert validate_block(block, genesis, genesis_state) is False


def test_ledger_add_and_get():
    """Test thêm và lấy blocks từ ledger"""
    ledger = Ledger()
    proposer = KeyPair()
    
    state0 = State()
    block0 = build_block(None, state0, [], proposer)
    
    ledger.add_block(block0, state0)
    
    assert ledger.get_block(0) == block0
    assert ledger.get_state(0) == state0
    assert ledger.get_block(1) is None
    assert ledger.get_state(1) is None


def test_ledger_latest_finalized():
    """Test lấy block finalized mới nhất"""
    ledger = Ledger()
    proposer = KeyPair()
    alice = KeyPair()
    
    # Thêm genesis
    state0 = State()
    block0 = build_block(None, state0, [], proposer)
    ledger.add_block(block0, state0)
    
    # Add block 1
    tx1 = SignedTx.create(TxBody(alice.pubkey(), "count", 1), alice)
    state1 = state0.copy()
    state1.apply_tx(tx1)
    block1 = build_block(block0, state0, [tx1], proposer)
    ledger.add_block(block1, state1)
    
    # Add block 2
    tx2 = SignedTx.create(TxBody(alice.pubkey(), "count", 2), alice)
    state2 = state1.copy()
    state2.apply_tx(tx2)
    block2 = build_block(block1, state1, [tx2], proposer)
    ledger.add_block(block2, state2)
    
    latest = ledger.latest_finalized()
    assert latest is not None
    latest_block, latest_state = latest
    
    assert latest_block.header.height == 2
    assert latest_state.get(alice.pubkey(), "count") == 2


def test_ledger_empty():
    """Test các phương thức ledger với ledger rỗng"""
    ledger = Ledger()
    
    assert ledger.latest_finalized() is None
    assert ledger.get_height() == -1


def test_block_hash_deterministic():
    """Test block hash là deterministic"""
    kp = KeyPair()
    state = State()
    
    block1 = build_block(None, state, [], kp)
    block2 = build_block(None, state, [], kp)
    
    # Blocks được tạo với cùng parameters nên có header content giống nhau
    # nhưng có chữ ký khác nhau (trừ khi dùng cùng nonce/randomness)
    # Tuy nhiên, block_hash chỉ dựa trên header
    assert block1.header == block2.header


def test_chain_building():
    """Test tạo một chuỗi các blocks"""
    ledger = Ledger()
    proposer = KeyPair()
    alice = KeyPair()
    
    # Genesis
    state = State()
    genesis = build_block(None, state, [], proposer)
    ledger.add_block(genesis, state)
    
    # Tạo chuỗi 5 blocks
    current_block = genesis
    current_state = state
    
    for i in range(1, 6):
        tx = SignedTx.create(TxBody(alice.pubkey(), "counter", i), alice)
        new_state = current_state.copy()
        new_state.apply_tx(tx)
        
        block = build_block(current_block, current_state, [tx], proposer)
        
        # Validate trước khi thêm
        assert validate_block(block, current_block, current_state) is True
        
        ledger.add_block(block, new_state)
        
        current_block = block
        current_state = new_state
    
    # Kiểm tra state cuối cùng
    assert ledger.get_height() == 5
    final_block, final_state = ledger.latest_finalized()
    assert final_block.header.height == 5
    assert final_state.get(alice.pubkey(), "counter") == 5
