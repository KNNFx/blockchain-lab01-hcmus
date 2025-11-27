class MockConsensus:
    def __init__(self, validator_keypair=None, total_validators=4, validator_index=0, on_finalize_callback=None, on_ask_for_block=None):
        self.finalized_blocks = []
        self.validator_keypair = validator_keypair
        self.total_validators = total_validators
        self.validator_index = validator_index
        self.on_finalize_callback = on_finalize_callback
        self.on_ask_for_block = on_ask_for_block

    def on_receive_block(self, block):
        # Mock: always accept
        return True

    def on_receive_vote(self, vote):
        # Mock: accept all votes but don't process logic
        pass

    def should_propose(self, height, round=0):
        # Mock: always ready to propose
        return True
        
    def get_finalized_count(self):
        return len(self.finalized_blocks)
        
    def get_latest_finalized(self):
        return self.finalized_blocks[-1] if self.finalized_blocks else None

    def finalize_block(self, block):
        # Helper for tests to manually finalize
        self.finalized_blocks.append(block)
        if self.on_finalize_callback:
            self.on_finalize_callback(block)