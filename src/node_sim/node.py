from mock.mock_core import MockCore
from mock.mock_block import MockBlockLayer
from mock.mock_consensus import MockConsensus

class Node:
    def __init__(self, node_id, network):
        self.id = node_id
        self.core = MockCore()
        self.blocklayer = MockBlockLayer()
        self.consensus = MockConsensus()
        network.register(self)

    def receive(self, message):
        print(f"[Node {self.id}] Received: {message}")
