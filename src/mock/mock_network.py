class MockNetwork:
    def __init__(self):
        self.subscribers = []

    def register(self, node):
        self.subscribers.append(node)

    def send(self, sender, receiver, message):
        # Không delay, không drop
        receiver.receive(message)

    def broadcast(self, sender, message):
        for node in self.subscribers:
            if node != sender:
                node.receive(message)
