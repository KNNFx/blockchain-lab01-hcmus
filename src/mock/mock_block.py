class MockBlockLayer:
    def build_block(self, parent_block, parent_state, txs):
        return {
            "height": parent_block["height"] + 1 if parent_block else 1,
            "txs": txs,
            "hash": "mock_block_hash",
            "state_hash": "mock_state_hash",
        }

    def validate_block(self, block):
        return True  # luôn hợp lệ