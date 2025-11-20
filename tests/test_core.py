from core import KeyPair, TxBody, SignedTx, State, canonical_json, verify_struct

def test_canonical_json_deterministic():
    """
    - "Define a single, unambiguous byte encoding for data included in hashes or signatures.
    Different nodes must produce the same bytes for the same logical content."
    """
    a = {"z": 1, "a": [3, 1]}
    b = {"a": [3, 1], "z": 1}
    assert canonical_json(a) == canonical_json(b)

def test_sign_verify_tx():
    """
    - "Every protocol message that affects state or consensus is signed:
    transactions, block headers, and votes."
    """
    kp = KeyPair()
    body = TxBody(sender_pubkey_hex=kp.pubkey(), key="msg", value="hello")
    tx = SignedTx.create(body, kp)
    assert tx.verify() is True

def test_wrong_context_rejected():
    """
    - "Use explicit context strings (domain separation)
    so a signature valid for one message type cannot be reused for another
    (e.g., TX:chain_id, HEADER:chain_id, VOTE:chain_id)."
    """
    kp = KeyPair()
    body = TxBody(sender_pubkey_hex=kp.pubkey(), key="x", value=1)
    tx = SignedTx.create(body, kp)
    
    forged = tx.__dict__.copy()
    forged["context"] = "HEADER:blockchain-lab01-hcmus"
    assert verify_struct("TX:", forged) is False

def test_state_ownership():
    """
    - "Alice sets "Alice/message"="hello"; later Bob sets "Bob/message"="hi"."
    - "Each transaction affects only data owned by its sender and
    must carry a valid signature in the TX:chain_id domain."
    """
    alice = KeyPair()
    bob = KeyPair()
    state = State()

    # Alice create key
    tx1 = SignedTx.create(TxBody(alice.pubkey(), "msg", "hello"), alice)
    assert state.apply_tx(tx1) is True

    # Bob tries to overwrite Alice's key → rejected because the signature is not Alice's
    bad_tx = SignedTx.create(TxBody(bob.pubkey(), "msg", "hacked by Bob"), bob)
    assert state.apply_tx(bad_tx) is False

    # Check Alice is still the owner
    full_key = f"{alice.pubkey()}/msg"
    assert state.data.get(full_key) == "hello"

def test_state_commitment_deterministic():
    """
    - "Each block header commits to the resulting state
    via a single state hash (your chosen commitment)."
    """
    state1 = State({"a/b": 1, "c/d": 2})
    state2 = State({"c/d": 2, "a/b": 1})
    assert state1.commitment() == state2.commitment()