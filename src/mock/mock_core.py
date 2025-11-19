class MockCore:
    def apply_tx(self, tx, state):
        # Mock: luôn chấp nhận tx và tăng counter
        new_state = dict(state)
        new_state["counter"] = new_state.get("counter", 0) + 1
        return new_state

    def commitment(self, state):
        # Mock: hash giả
        return "mock_state_hash"
