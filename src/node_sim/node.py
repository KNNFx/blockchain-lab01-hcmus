from mock.mock_core import MockCore
from mock.mock_block import MockBlockLayer
from mock.mock_consensus import MockConsensus

class Node:
    def __init__(self, node_id, network):
        self.id = node_id #
        self.core = MockCore() #
        self.blocklayer = MockBlockLayer() #
        self.consensus = MockConsensus() #
        #################
        self.mempool = [] #
        self.network = network #
        #################
        network.register(self) #

    def receive(self, message):
        print(f"[Node {self.id}] Received: {message}") #
        ##############################################
        msg_type = message.get("type") #
        data = message.get("data") #

        if msg_type == "TX": #
            self.mempool.append(data) #
            print(f"[Node {self.id}] Added TX to mempool. Size: {len(self.mempool)}") #
        
        elif msg_type == "BLOCK": #
            if self.blocklayer.validate_block(data): #
                print(f"[Node {self.id}] Block validated.") #
                # In a real system, we would process the block here #
            else: #
                print(f"[Node {self.id}] Block invalid.") #

        elif msg_type == "VOTE": #
            self.consensus.receive_vote(data) #
            print(f"[Node {self.id}] Vote received.") #

    def propose_block(self):
        # Mock logic: Create a block from all txs in mempool #
        if not self.mempool: #
            print(f"[Node {self.id}] Mempool empty, nothing to propose.") #
            return #

        # Mock parent block (None for genesis) and state #
        parent_block = None #
        parent_state = {} #
        
        block = self.blocklayer.build_block(parent_block, parent_state, self.mempool) #
        print(f"[Node {self.id}] Proposing block: {block['hash']}") #
        
        if self.consensus.propose_block(block): #
            self.network.broadcast(self, {"type": "BLOCK", "data": block}) #
            self.mempool = [] # Clear mempool after proposal (mock logic) #
