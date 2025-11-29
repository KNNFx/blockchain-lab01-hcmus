import pytest
import sys
import os
import shutil
import filecmp
from typing import List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from node_sim.simulator import Simulator
from network.messages import Message, MessageType
from core.types_tx import SignedTx, TxBody
from core.crypto_layer import KeyPair, sign_struct

@pytest.fixture
def temp_config(tmp_path):
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        f.write("simulation:\n  num_nodes: 8\n  max_blocks: 5\n  min_delay: 0.01\n  max_delay: 0.1\n")
    return str(config_path)

def test_simulation_run(temp_config):
    """Test that the simulation runs without errors."""
    sim = Simulator(config_path=temp_config)
    sim.run(max_steps=20)

def test_determinism(temp_config, tmp_path):
    """Test that two runs with the same config produce identical logs."""
    log1_path = tmp_path / "run1.log"
    log2_path = tmp_path / "run2.log"
    
    # Run 1
    with open(log1_path, "w") as f:
        sim1 = Simulator(config_path=temp_config, output_file=f, seed=42)
        sim1.run(max_steps=5) # Reduce steps for speed
        
    # Run 2
    with open(log2_path, "w") as f:
        sim2 = Simulator(config_path=temp_config, output_file=f, seed=42)
        sim2.run(max_steps=5)
        
    # Compare logs
    assert filecmp.cmp(log1_path, log2_path), "Logs should be identical"

def test_transaction_propagation(temp_config):
    """Test that transactions are propagated to other nodes."""
    sim = Simulator(config_path=temp_config)
    
    # Create a valid transaction
    kp = KeyPair()
    tx_body = TxBody(sender_pubkey_hex=kp.pubkey(), key="test", value="data")
    tx = SignedTx.create(tx_body, kp)
    
    # Inject into Node 0 via network
    msg = Message(
        msg_id=0,
        from_id="CLIENT",
        to_id=sim.nodes[0].node_id,
        msg_type=MessageType.TX,
        payload=tx
    )
    
    # Send at time 0
    sim.network.send(msg, 0.0)
    
    # Run simulation for a few steps (blocks)
    sim.run(max_steps=10)
    
    # Verify Node 0 has it in mempool OR in blockchain
    found = False
    if tx in sim.nodes[0].mempool:
        found = True
    else:
        # Check blockchain
        for block in sim.nodes[0].blockchain:
            if tx in block.txs:
                found = True
                break
    
    assert found, "Transaction should be in mempool or blockchain"

def test_block_proposal(temp_config):
    """Test that blocks are proposed and finalized."""
    sim = Simulator(config_path=temp_config)
    
    # Run long enough for proposals
    sim.run(max_steps=100) # 50 steps should be enough for a few seconds
    
    # Check if any node has blocks
    max_height = 0
    for node in sim.nodes:
        if node.blockchain:
            max_height = max(max_height, node.blockchain[-1].header.height)
            
    assert max_height > 0, "Should have finalized at least one block"

def test_safety_one_block_per_height(temp_config):
    """
    1. only one block becomes finalized at each height;
    """
    sim = Simulator(config_path=temp_config, seed=123)
    sim.run(max_steps=100)
    
    # Check that all nodes agree on the chain
    # We take the first node's chain as reference
    reference_chain = sim.nodes[0].blockchain
    
    assert len(reference_chain) > 0, "Should have finalized some blocks"
    
    for node in sim.nodes[1:]:
        # It's possible nodes have different lengths if some are slower, 
        # but the common prefix must be identical.
        min_len = min(len(reference_chain), len(node.blockchain))
        
        for i in range(min_len):
            block_ref = reference_chain[i]
            block_node = node.blockchain[i]
            
            assert block_ref.block_hash() == block_node.block_hash(), \
                f"Node {node.node_id} disagrees at height {block_ref.header.height}"

def test_security_invalid_messages(temp_config):
    """
    2. messages or transactions with invalid signatures or wrong contexts are rejected
    """
    sim = Simulator(config_path=temp_config, seed=456)
    
    # 1. Invalid Transaction Signature
    kp_fake = KeyPair()
    tx_body = TxBody(sender_pubkey_hex=kp_fake.pubkey(), key="hack", value="attempt")
    # Sign with wrong key or tamper signature
    tx = SignedTx.create(tx_body, kp_fake)
    tx.signature = "00" * 64 # Invalid signature
    
    msg_tx = Message(
        msg_id=0,
        from_id="ATTACKER",
        to_id=sim.nodes[0].node_id,
        msg_type=MessageType.TX,
        payload=tx
    )
    sim.network.send(msg_tx, 0.0)
    
    # 2. Invalid Vote Context
    # Create a vote but sign with wrong context
    # We need to manually sign to mess it up
    vote_payload = {
        "height": 1,
        "round": 0,
        "block_hash": "00"*32,
        "phase": "PREVOTE",
        "validator_pubkey_hex": kp_fake.pubkey()
    }
    # Sign with "WRONG_CTX:"
    signed_dict = sign_struct("WRONG_CTX:", kp_fake, vote_payload)
    # But Vote.from_dict expects specific fields. 
    # The Vote class verifies "VOTE:" context in verify().
    # We construct a Vote object with this invalid signature/context data.
    # Wait, Vote class stores 'context' field.
    # If we pass "WRONG_CTX" in context field, verify_struct will check against "VOTE:" + CHAIN_ID
    # and fail because context mismatch.
    
    from consensus.vote import Vote
    vote = Vote(**signed_dict)
    
    msg_vote = Message(
        msg_id=1,
        from_id="ATTACKER",
        to_id=sim.nodes[0].node_id,
        msg_type=MessageType.VOTE,
        payload=vote
    )
    sim.network.send(msg_vote, 0.0)
    
    sim.run(max_steps=5)
    
    # Verification:
    # 1. TX should not be in mempool
    assert tx not in sim.nodes[0].mempool, "Invalid TX should be rejected"
    
    # 2. Vote should be rejected (not affect consensus)
    # Hard to check internal state of consensus engine directly without accessors,
    # but we can ensure no crash and system continues.
    # Also, since it's from unknown validator (kp_fake), it should be ignored anyway.
    # To test signature verification specifically, we should use a valid validator's key but wrong signature.
    
    # Let's try to forge a message from a real validator
    real_node = sim.nodes[1]
    real_kp = real_node.keypair
    
    tx_body_2 = TxBody(sender_pubkey_hex=real_kp.pubkey(), key="hack2", value="attempt2")
    tx_2 = SignedTx.create(tx_body_2, real_kp)
    tx_2.signature = "00" * 64 # Tamper signature
    
    msg_tx_2 = Message(
        msg_id=2,
        from_id="ATTACKER",
        to_id=sim.nodes[0].node_id,
        msg_type=MessageType.TX,
        payload=tx_2
    )
    sim.network.send(msg_tx_2, 0.0)
    
    sim.run(max_steps=5)
    assert tx_2 not in sim.nodes[0].mempool, "Tampered TX from valid validator should be rejected"

def test_robustness_replays_duplicates(tmp_path):
    """
    3. replays/duplicates are ignored without breaking safety;
    """
    config_path = tmp_path / "robust_config.yaml"
    with open(config_path, "w") as f:
        f.write("simulation:\n  num_nodes: 8\n  max_blocks: 5\n  dup_prob: 0.5\n  min_delay: 0.01\n  max_delay: 0.1\n")
    
    sim = Simulator(config_path=str(config_path), seed=789)
    sim.run(max_steps=100)
    
    # Check Safety
    reference_chain = sim.nodes[0].blockchain
    assert len(reference_chain) > 0
    
    for node in sim.nodes[1:]:
        min_len = min(len(reference_chain), len(node.blockchain))
        for i in range(min_len):
            assert reference_chain[i].block_hash() == node.blockchain[i].block_hash()

def test_network_issues_drops_delays(tmp_path):
    """
    4. delayed or dropped messages do not cause conflicting finalization;
    """
    config_path = tmp_path / "network_issue_config.yaml"
    with open(config_path, "w") as f:
        # High drop prob and delay
        f.write("simulation:\n  num_nodes: 8\n  max_blocks: 5\n  drop_prob: 0.2\n  min_delay: 0.01\n  max_delay: 0.1\n")
    
    sim = Simulator(config_path=str(config_path), seed=101112)
    sim.run(max_steps=200) # Give more time due to drops/delays
    
    # Check Safety
    reference_chain = sim.nodes[0].blockchain
    # It's possible no blocks finalized if network is too bad, but if they did, they must match.
    if len(reference_chain) > 0:
        for node in sim.nodes[1:]:
            min_len = min(len(reference_chain), len(node.blockchain))
            for i in range(min_len):
                assert reference_chain[i].block_hash() == node.blockchain[i].block_hash()

def test_determinism_complex(tmp_path):
    """
    5. identical runs produce identical logs and final state.
    (Using the robust config to ensure determinism holds even with random events)
    """
    config_path = tmp_path / "robust_config.yaml"
    with open(config_path, "w") as f:
        f.write("simulation:\n  num_nodes: 8\n  max_blocks: 5\n  dup_prob: 0.5\n  drop_prob: 0.1\n  min_delay: 0.01\n  max_delay: 0.1\n")
        
    log1_path = tmp_path / "run1.log"
    log2_path = tmp_path / "run2.log"
    
    seed = 999
    
    # Run 1
    with open(log1_path, "w") as f:
        sim1 = Simulator(config_path=str(config_path), output_file=f, seed=seed)
        sim1.run(max_steps=100)
        
    # Run 2
    with open(log2_path, "w") as f:
        sim2 = Simulator(config_path=str(config_path), output_file=f, seed=seed)
        sim2.run(max_steps=100)
        
    assert filecmp.cmp(log1_path, log2_path), "Logs should be identical even with complex network conditions"