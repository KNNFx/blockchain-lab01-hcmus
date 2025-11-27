import sys
import os
import unittest
from collections import defaultdict

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from consensus.consensus import ConsensusEngine
from consensus.vote import build_vote, PHASE_PREVOTE, PHASE_PRECOMMIT
from core.crypto_layer import KeyPair

class MockBlock:
    def __init__(self, height, block_hash):
        self.header = type('obj', (object,), {'height': height})
        self._hash = block_hash
    
    def block_hash(self):
        return self._hash

class TestConsensus(unittest.TestCase):
    def setUp(self):
        self.validator_kp = KeyPair()
        self.engine = ConsensusEngine(self.validator_kp, total_validators=4, validator_index=0)

    def test_basic_flow(self):
        print("\n=== Testing Basic Consensus Flow ===")
        
        # 1. Propose Block 0
        block_0 = MockBlock(height=0, block_hash="block_0")
        self.engine.on_receive_block(block_0)
        
        # Verify we prevoted
        self.assertIsNotNone(self.engine.my_prevote)
        self.assertEqual(self.engine.my_prevote, "block_0")
        print("[PASS] Proposed and Prevoted")
        
        # 2. Receive Prevotes (Need 3 total for 2/3+)
        # We already have our own prevote (conceptually, though engine doesn't count it in pool unless we feed it back)
        # For simplicity, let's feed 3 external votes
        voters = [KeyPair() for _ in range(3)]
        precommit_vote_received = False
        
        for kp in voters:
            vote = build_vote(0, 0, "block_0", PHASE_PREVOTE, kp)
            res = self.engine.on_receive_vote(vote)
            if res:
                # Expect a Precommit vote when 2/3+ reached
                self.assertEqual(res.phase, PHASE_PRECOMMIT)
                self.assertEqual(res.block_hash, "block_0")
                precommit_vote_received = True
        
        # Verify precommit was triggered and sent
        self.assertTrue(precommit_vote_received, "Expected precommit vote after 2/3+ prevotes")
        self.assertEqual(self.engine.my_precommit, "block_0")
        print("[PASS] Precommit sent after supermajority prevotes")
        
        # 3. Receive Precommits
        for kp in voters:
            vote = build_vote(0, 0, "block_0", PHASE_PRECOMMIT, kp)
            res = self.engine.on_receive_vote(vote)
            # Finalization might return None or a list of votes (if next height buffered)
            
        # Verify Finalization
        self.assertEqual(self.engine.get_finalized_count(), 1)
        self.assertEqual(self.engine.get_latest_finalized().block_hash(), "block_0")
        print("[PASS] Block finalized after supermajority precommits")

    def test_vote_buffering(self):
        print("\n=== Testing Vote Buffering ===")
        
        # 1. Create votes for Height 1 (Future)
        future_vote = build_vote(
            height=1,
            round=0,
            block_hash="future_block_hash",
            phase=PHASE_PREVOTE,
            keypair=self.validator_kp
        )
        
        # 2. Send future vote
        self.engine.on_receive_vote(future_vote)
        
        # Verify it's buffered
        self.assertIn((1, 0), self.engine.future_vote_buffer)
        print("[PASS] Vote buffered successfully")
            
        # 3. Simulate finalizing Height 0 to move to Height 1
        # Mock a block for Height 0
        self.engine.proposed_blocks["block_0"] = MockBlock(height=0, block_hash="block_0")
        self.engine._finalize_block("block_0", 0)
        
        # 4. Verify buffer was processed
        pool = self.engine._get_vote_pool(1, 0)
        self.assertEqual(pool.get_prevote_count("future_block_hash"), 1)
        print("[PASS] Buffered vote processed successfully after height change")

    def test_block_buffering(self):
        print("\n=== Testing Block Buffering ===")
        
        # 1. Create block for Height 1 (Future)
        future_block = MockBlock(height=1, block_hash="block_1")
        
        # 2. Receive future block
        self.engine.on_receive_block(future_block)
        
        # Verify it's buffered
        self.assertIn(1, self.engine.future_block_buffer)
        print("[PASS] Block buffered successfully")
            
        # Verify we didn't jump height
        self.assertEqual(self.engine.current_height, 0)
        print("[PASS] Height remained at 0")

        # 3. Simulate finalizing Height 0
        self.engine.proposed_blocks["block_0"] = MockBlock(height=0, block_hash="block_0")
        self.engine._finalize_block("block_0", 0)
        
        # 4. Verify buffer was processed
        self.assertEqual(self.engine.my_prevote, "block_1")
        print("[PASS] Buffered block processed successfully (Prevote sent)")

    def test_fast_forward(self):
        print("\n=== Testing Fast Forward ===")
        
        # 1. Propose Block 0 (Current Height)
        block_0 = MockBlock(height=0, block_hash="block_0")
        self.engine.on_receive_block(block_0)
        
        # 2. Simulate Supermajority for Height 1 (Future)
        # We need 3 votes (Total 4, 2/3+ is 3)
        voters = [KeyPair() for _ in range(3)]
        
        for kp in voters:
            vote = build_vote(
                height=1,
                round=0,
                block_hash="block_1",
                phase=PHASE_PRECOMMIT,
                keypair=kp
            )
            self.engine.on_receive_vote(vote)
            
        # 3. Verify Fast Forward triggered
        # Height 0 should be finalized automatically
        self.assertEqual(self.engine.get_finalized_count(), 1)
        self.assertEqual(self.engine.get_latest_finalized().block_hash(), "block_0")
        print("[PASS] Fast Forward successful: Height 0 finalized automatically")

    def test_block_fetching(self):
        print("\n=== Testing Block Fetching ===")
        
        requested_blocks = []
        def mock_ask_for_block(block_hash):
            print(f"Callback: Asking for block {block_hash}")
            requested_blocks.append(block_hash)
            
        # Setup new engine with callback
        engine = ConsensusEngine(self.validator_kp, total_validators=4, validator_index=0, on_ask_for_block=mock_ask_for_block)
        
        # 1. Try to finalize a missing block
        engine._finalize_block("missing_block", 0)
        
        # Verify request was made
        self.assertIn("missing_block", requested_blocks)
        print("[PASS] Block requested via callback")
            
        # Verify NOT finalized yet
        self.assertEqual(engine.get_finalized_count(), 0)
        print("[PASS] Finalization paused (waiting for block)")
            
        # 2. Provide the missing block
        missing_block = MockBlock(height=0, block_hash="missing_block")
        engine.on_receive_block(missing_block)
        
        # 3. Verify Finalization resumed and completed
        self.assertEqual(engine.get_finalized_count(), 1)
        self.assertEqual(engine.get_latest_finalized().block_hash(), "missing_block")
        print("[PASS] Finalization resumed and completed after receiving block")

    def test_advanced_block_fetching(self):
        print("\n=== Testing Advanced Block Fetching (Parent Hash) ===")
        
        requested_blocks = []
        def mock_ask_for_block(block_hash):
            print(f"Callback: Asking for block {block_hash}")
            requested_blocks.append(block_hash)
            
        engine = ConsensusEngine(self.validator_kp, total_validators=4, validator_index=0, on_ask_for_block=mock_ask_for_block)
        
        # 1. Receive Future Block 1 (which points to Block 0)
        # MockBlock doesn't have parent_hash by default, so we attach it
        block_1 = MockBlock(height=1, block_hash="block_1")
        block_1.header.parent_hash = "block_0_hash" # This is what we want to fetch
        
        engine.on_receive_block(block_1)
        print("Received Future Block 1 with parent_hash='block_0_hash'")
        
        # 2. Simulate Supermajority for Height 1
        # This triggers Fast Forward
        print("Simulating supermajority for Height 1...")
        voters = [KeyPair() for _ in range(3)]
        for kp in voters:
            vote = build_vote(1, 0, "block_1", PHASE_PRECOMMIT, kp)
            engine.on_receive_vote(vote)
            
        # 3. Verify that it requested "block_0_hash"
        if "block_0_hash" in requested_blocks:
            print("[PASS] Correctly extracted parent_hash and requested missing block")
        else:
            print(f"[FAIL] Did not request parent hash. Requested: {requested_blocks}")
            self.fail("Did not request parent hash")

    def test_locking_safety(self):
        """Test that locking prevents voting for conflicting blocks"""
        print("\n=== Testing Locking Safety ===")
        
        # 1. Propose and receive block_A
        block_a = MockBlock(height=0, block_hash="block_A")
        vote_a = self.engine.on_receive_block(block_a)
        self.assertIsNotNone(vote_a)
        self.assertEqual(vote_a.block_hash, "block_A")
        print("[PASS] Prevoted for block_A")
        
        # 2. Receive 3 prevotes for block_A -> triggers lock
        voters = [KeyPair() for _ in range(3)]
        for kp in voters:
            vote = build_vote(0, 0, "block_A", PHASE_PREVOTE, kp)
            res = self.engine.on_receive_vote(vote)
        
        # Verify locked to block_A
        self.assertEqual(self.engine.locked_block, "block_A")
        self.assertEqual(self.engine.locked_round, 0)
        self.assertEqual(self.engine.valid_block, "block_A")
        print("[PASS] Locked to block_A after 2/3+ prevotes")
        
        # 3. Advance to new round (simulate timeout)
        self.engine.advance_round()
        self.assertEqual(self.engine.current_round, 1)
        
        # 4. Try to receive conflicting block_B in round 1
        # Should prevote NIL because locked to block_A
        block_b = MockBlock(height=0, block_hash="block_B")
        vote_b = self.engine.on_receive_block(block_b)
        
        self.assertIsNotNone(vote_b)
        self.assertEqual(vote_b.block_hash, "NIL")
        self.assertEqual(vote_b.round, 1)
        print("[PASS] Prevoted NIL for conflicting block_B (locked to block_A)")
        
        # 5. Verify still locked to block_A
        self.assertEqual(self.engine.locked_block, "block_A")
        print("[PASS] Locking prevents voting for conflicting blocks")

    def test_round_advancement(self):
        """Test advancing rounds for liveness"""
        print("\n=== Testing Round Advancement ===")
        
        # Start at height 0, round 0
        self.assertEqual(self.engine.current_height, 0)
        self.assertEqual(self.engine.current_round, 0)
        print("[PASS] Initial state: height 0, round 0")
        
        # Simulate some voting without reaching consensus
        block = MockBlock(height=0, block_hash="block_0")
        self.engine.on_receive_block(block)
        self.assertIsNotNone(self.engine.my_prevote)
        
        # Advance to round 1 (timeout scenario)
        votes = self.engine.advance_round()
        self.assertEqual(self.engine.current_round, 1)
        print("[PASS] Advanced to round 1")
        
        # Vote state should reset
        self.assertIsNone(self.engine.my_prevote)
        self.assertIsNone(self.engine.my_precommit)
        print("[PASS] Vote state reset after round advancement")
        
        # Advance to round 2
        self.engine.advance_round()
        self.assertEqual(self.engine.current_round, 2)
        print("[PASS] Advanced to round 2")
        
        # Height should remain the same
        self.assertEqual(self.engine.current_height, 0)
        print("[PASS] Height unchanged across rounds")

    def test_proposer_selection(self):
        """Test round-robin proposer selection"""
        print("\n=== Testing Proposer Selection ===")
        
        # Validator 0 at height 0, round 0
        self.assertTrue(self.engine.should_propose(0, 0))  # (0+0) % 4 = 0 ✓
        print("[PASS] Validator 0 proposes at (h=0, r=0)")
        
        # Validator 0 at height 0, round 1
        self.assertFalse(self.engine.should_propose(0, 1))  # (0+1) % 4 = 1 ✗
        print("[PASS] Validator 0 doesn't propose at (h=0, r=1)")
        
        # Validator 0 at height 1, round 3
        self.assertTrue(self.engine.should_propose(1, 3))  # (1+3) % 4 = 0 ✓
        print("[PASS] Validator 0 proposes at (h=1, r=3)")
        
        # Test with different validator indices
        engine1 = ConsensusEngine(KeyPair(), 4, validator_index=1)
        self.assertTrue(engine1.should_propose(0, 1))  # (0+1) % 4 = 1 ✓
        self.assertFalse(engine1.should_propose(0, 0))  # (0+0) % 4 = 0 ✗
        print("[PASS] Validator 1 proposes at (h=0, r=1)")
        
        engine2 = ConsensusEngine(KeyPair(), 4, validator_index=2)
        self.assertTrue(engine2.should_propose(0, 2))  # (0+2) % 4 = 2 ✓
        self.assertFalse(engine2.should_propose(0, 0))  # (0+0) % 4 = 0 ✗
        print("[PASS] Validator 2 proposes at (h=0, r=2)")
        
        engine3 = ConsensusEngine(KeyPair(), 4, validator_index=3)
        self.assertTrue(engine3.should_propose(0, 3))  # (0+3) % 4 = 3 ✓
        self.assertFalse(engine3.should_propose(0, 0))  # (0+0) % 4 = 0 ✗
        print("[PASS] Validator 3 proposes at (h=0, r=3)")
        
        # Test with no validator_index set
        engine_none = ConsensusEngine(KeyPair(), 4, validator_index=None)
        self.assertFalse(engine_none.should_propose(0, 0))
        print("[PASS] Engine without validator_index doesn't propose")

    def test_nil_votes(self):
        """Test that supermajority NIL votes are handled correctly"""
        print("\n=== Testing NIL Votes ===")
        
        voters = [KeyPair() for _ in range(3)]
        
        # Send 3 prevotes for NIL (no valid block)
        for kp in voters:
            vote = build_vote(0, 0, "NIL", PHASE_PREVOTE, kp)
            res = self.engine.on_receive_vote(vote)
        
        # Should NOT trigger precommit (leader is NIL)
        self.assertIsNone(self.engine.my_precommit)
        print("[PASS] NIL prevotes don't trigger precommit")
        
        # Verify NIL is counted properly
        pool = self.engine._get_vote_pool(0, 0)
        self.assertEqual(pool.get_prevote_count("NIL"), 3)
        self.assertTrue(pool.has_supermajority_prevotes("NIL"))
        print("[PASS] NIL votes counted and supermajority detected")

    def test_duplicate_vote_rejection(self):
        """Test that duplicate votes from same validator are rejected"""
        print("\n=== Testing Duplicate Vote Rejection ===")
        
        kp = KeyPair()
        pool = self.engine._get_vote_pool(0, 0)
        
        # Send first prevote
        vote1 = build_vote(0, 0, "block_0", PHASE_PREVOTE, kp)
        result1 = pool.add_vote(vote1)
        self.assertTrue(result1)
        self.assertEqual(pool.get_prevote_count("block_0"), 1)
        print("[PASS] First prevote accepted")
        
        # Try to send another prevote from same validator for different block
        vote2 = build_vote(0, 0, "block_1", PHASE_PREVOTE, kp)
        result2 = pool.add_vote(vote2)
        self.assertFalse(result2)
        self.assertEqual(pool.get_prevote_count("block_1"), 0)
        print("[PASS] Duplicate prevote rejected")
        
        # Should still only have 1 prevote for block_0
        self.assertEqual(pool.get_prevote_count("block_0"), 1)
        print("[PASS] Original vote unchanged")
        
        # Test same for precommits
        precommit1 = build_vote(0, 0, "block_0", PHASE_PRECOMMIT, kp)
        result3 = pool.add_vote(precommit1)
        self.assertTrue(result3)
        print("[PASS] First precommit accepted")
        
        precommit2 = build_vote(0, 0, "block_1", PHASE_PRECOMMIT, kp)
        result4 = pool.add_vote(precommit2)
        self.assertFalse(result4)
        print("[PASS] Duplicate precommit rejected")

    def test_old_vote_rejection(self):
        """Test that old/past votes are ignored"""
        print("\n=== Testing Old Vote Rejection ===")
        
        # Finalize block at height 0
        block_0 = MockBlock(height=0, block_hash="block_0")
        self.engine.proposed_blocks["block_0"] = block_0
        self.engine._finalize_block("block_0", 0)
        
        # Now at height 1
        self.assertEqual(self.engine.current_height, 1)
        print("[PASS] Moved to height 1")
        
        # Try to send vote for height 0 (past)
        old_vote = build_vote(0, 0, "block_old", PHASE_PREVOTE, KeyPair())
        result = self.engine.on_receive_vote(old_vote)
        
        # Should be ignored (return None)
        self.assertIsNone(result)
        print("[PASS] Old vote ignored")
        
        # Verify it wasn't added to any pool
        # Height 1, round 0 pool should be empty
        pool = self.engine._get_vote_pool(1, 0)
        self.assertEqual(len(pool.all_votes), 0)
        print("[PASS] Old vote not added to pool")

    def test_old_block_rejection(self):
        """Test that old/past blocks are ignored"""
        print("\n=== Testing Old Block Rejection ===")
        
        # Finalize block at height 0
        block_0 = MockBlock(height=0, block_hash="block_0")
        self.engine.proposed_blocks["block_0"] = block_0
        self.engine._finalize_block("block_0", 0)
        
        # Now at height 1
        self.assertEqual(self.engine.current_height, 1)
        
        # Try to receive block for height 0 (past)
        old_block = MockBlock(height=0, block_hash="old_block")
        result = self.engine.on_receive_block(old_block)
        
        # Should be ignored (return None)
        self.assertIsNone(result)
        print("[PASS] Old block ignored")
        
        # Verify prevote wasn't generated
        self.assertIsNone(self.engine.my_prevote)
        print("[PASS] No prevote for old block")

if __name__ == "__main__":
    unittest.main()
