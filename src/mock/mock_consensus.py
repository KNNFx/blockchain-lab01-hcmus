class MockConsensus:
    def __init__(self):
        pass

    def propose_block(self, block):
        # Mock: always propose
        return True

    def receive_vote(self, vote):
        # Mock: accept all votes
        pass