class Simulator:
    def __init__(self, network, nodes):
        self.network = network
        self.nodes = nodes

    def tick(self):
        # Mock tick: broadcast a test message from first node
        if self.nodes:
            self.network.broadcast(self.nodes[0], {"type": "TICK", "data": "simulation step"})
