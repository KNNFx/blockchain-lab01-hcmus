import sys
import os
import pytest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")

from consensus.consensus import ConsensusEngine
from consensus.vote import Vote, PHASE_PREVOTE, PHASE_PRECOMMIT, build_vote
from core.crypto_layer import KeyPair

def test_consensus_engine_flow():
    """
    Unit test for ConsensusEngine without the real network.
    We simulate the flow by calling engine methods directly.
    """
    
    # 1. Setup
    total_validators = 4
    keypair = KeyPair()
    
    # Mock callback
    mock_finalize = MagicMock()
    
    engine = ConsensusEngine(
        validator_keypair=keypair,
        total_validators=total_validators,
        on_finalize_callback=mock_finalize
    )
    
    # 2. Receive Block Proposal
    block = {
        "hash": "block_hash_1",
        "height": 1,
        "data": "Transaction Data"
    }
    
    # Engine should vote PREVOTE upon receiving a valid block
    did_prevote = engine.on_receive_block(block)
    assert did_prevote is True
    assert engine.my_prevote == "block_hash_1"
    
    # 3. Simulate receiving PREVOTES from other validators
    # We need 2/3 + 1 = 3 votes (including our own, which is implicit in the logic usually, 
    # but here the engine tracks incoming votes. Does it count its own?
    # Let's check consensus.py logic. It counts votes in the pool. 
    # Usually we need to feed our own vote back into the engine or the engine adds it automatically.
    # Looking at consensus.py, on_receive_block sets self.my_prevote but DOES NOT add it to the pool.
    # So we need to "receive" our own vote or rely on the loopback from the network.
    # In a unit test, we must manually feed it.
    
    # Create other validators' keypairs
    other_keypairs = [KeyPair() for _ in range(total_validators - 1)]
    all_keypairs = [keypair] + other_keypairs
    
    # Feed PREVOTES
    # We need 3 prevotes to trigger PRECOMMIT
    # Let's feed 3 votes (including ours if we want, or just 3 others)
    
    # Vote 1 (Ours - manually fed back)
    vote1 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, keypair)
    action = engine.on_receive_vote(vote1)
    assert action is None # Not enough yet
    
    # Vote 2
    vote2 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, other_keypairs[0])
    action = engine.on_receive_vote(vote2)
    assert action is None
    
    # Vote 3 (This should trigger PRECOMMIT)
    vote3 = build_vote(1, 0, "block_hash_1", PHASE_PREVOTE, other_keypairs[1])
    action = engine.on_receive_vote(vote3)
    
    assert action == "PREVOTE_READY"
    assert engine.my_precommit == "block_hash_1"
    
    # 4. Simulate receiving PRECOMMITS
    # We need 3 precommits to FINALIZE
    
    # Vote 1 (Ours - manually fed back)
    # Note: In real logic, we would build this vote because action was PREVOTE_READY
    commit1 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, keypair)
    action = engine.on_receive_vote(commit1)
    assert action is None
    
    # Vote 2
    commit2 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, other_keypairs[0])
    action = engine.on_receive_vote(commit2)
    assert action is None
    
    # Vote 3 (This should trigger FINALIZE)
    commit3 = build_vote(1, 0, "block_hash_1", PHASE_PRECOMMIT, other_keypairs[1])
    action = engine.on_receive_vote(commit3)
    
    assert action == "FINALIZE"
    assert engine.get_finalized_count() == 1
    assert engine.get_latest_finalized()["hash"] == "block_hash_1"
    
    # Verify callback was called
    mock_finalize.assert_called_once_with(block)

if __name__ == "__main__":
    test_consensus_engine_flow()
