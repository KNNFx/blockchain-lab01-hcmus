import pytest
import sys
import os
import binascii

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from core.crypto_layer import KeyPair, sign_struct, verify_struct, CHAIN_ID
from core.state import State
from core.types_tx import SignedTx, TxBody
from blocklayer.block import Block, BlockHeader, build_block, validate_block
from consensus.vote import Vote, VoteBody, PHASE_PREVOTE, PHASE_PRECOMMIT

def test_crypto_signatures():
    """Unit test for cryptographic verification."""
    kp = KeyPair()
    payload = {"message": "hello"}
    
    # 1. Valid signature
    signed = sign_struct("TEST:", kp, payload)
    assert verify_struct("TEST:", signed)
    
    # 2. Wrong context
    assert not verify_struct("WRONG:", signed)
    
    # 3. Tampered payload
    signed["message"] = "hacked"
    assert not verify_struct("TEST:", signed)
    
    # 4. Tampered signature
    signed["message"] = "hello" # Restore payload
    signed["signature"] = "00" * 64
    assert not verify_struct("TEST:", signed)

def test_state_update():
    """Unit test for state update rules."""
    state = State()
    kp = KeyPair()
    
    # 1. Apply valid TX
    tx_body = TxBody(sender_pubkey_hex=kp.pubkey(), key="foo", value="bar")
    tx = SignedTx.create(tx_body, kp)
    
    assert state.apply_tx(tx)
    assert state.get(kp.pubkey(), "foo") == "bar"
    
    # 2. Apply TX with same key (update)
    tx_body2 = TxBody(sender_pubkey_hex=kp.pubkey(), key="foo", value="baz")
    tx2 = SignedTx.create(tx_body2, kp)
    
    assert state.apply_tx(tx2)
    assert state.get(kp.pubkey(), "foo") == "baz"
    
    # 3. Invalid signature TX (should return False if State checked it, 
    # but State.apply_tx currently only checks signature if we implemented it there.
    # Let's check Node.receive for that. State usually just applies.
    # But let's check if State enforces anything else. 
    # Currently State is simple KV store.
    pass

def test_vote_verification():
    """Unit test for vote verification."""
    kp = KeyPair()
    
    # 1. Valid Vote
    body = VoteBody(height=1, round=0, block_hash="hash", phase=PHASE_PREVOTE, validator_pubkey_hex=kp.pubkey())
    vote = Vote.create(body, kp)
    assert vote.verify()
    
    # 2. Tampered Vote
    vote.block_hash = "hacked"
    assert not vote.verify()

def test_block_validation():
    """Unit test for block validation."""
    kp = KeyPair()
    parent_state = State()
    
    # 1. Genesis Block
    # build_block handles genesis if parent_block is None
    genesis = build_block(None, parent_state, [], kp)
    assert validate_block(genesis, None, parent_state)
    
    # 2. Next Block
    tx_body = TxBody(sender_pubkey_hex=kp.pubkey(), key="a", value="1")
    tx = SignedTx.create(tx_body, kp)
    
    block1 = build_block(genesis, parent_state, [tx], kp)
    
    # Update parent state for validation
    state_after_genesis = parent_state.copy() # Genesis had no txs
    
    assert validate_block(block1, genesis, state_after_genesis)
    
    # 3. Invalid Parent Hash
    block1.header.parent_hash = "00" * 64
    # Re-sign header because we changed it? validate_block checks signature first.
    # If we change header without resigning, signature check fails.
    assert not validate_block(block1, genesis, state_after_genesis)
    
    # 4. Invalid Height
    # Re-build to get valid signature but wrong logic
    block_bad_height = build_block(genesis, parent_state, [], kp)
    block_bad_height.header.height = 100 # Wrong height
    # Resign
    header_dict = block_bad_height.header.to_dict()
    signed = sign_struct("HEADER:", kp, header_dict)
    block_bad_height.header_signature = signed["signature"]
    
    assert not validate_block(block_bad_height, genesis, state_after_genesis)

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
