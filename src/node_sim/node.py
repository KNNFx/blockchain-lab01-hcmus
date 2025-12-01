from typing import List, Optional
import binascii

from network.network import Node as NetworkNode
from network.messages import Message, MessageType
from consensus.consensus import ConsensusEngine
from blocklayer.block import Block, build_block, validate_block
from core.state import State
from core.crypto_layer import KeyPair
from core.types_tx import SignedTx

class Node:
    def __init__(self, node_id: str, network, keypair: KeyPair, validators: List[str], gossip_k: int = 3):
        self.node_id = node_id # String ID for network
        self.network = network
        self.keypair = keypair
        self.validators = validators
        self.gossip_k = gossip_k  # Number of peers to gossip to
        
        # Initialize State and Blockchain
        self.state = State() # Genesis state
        self.blockchain: List[Block] = [] # Genesis block is usually implicit or added explicitly
        
        # Initialize Consensus Engine
        self.consensus = ConsensusEngine(
            validator_keypair=self.keypair,
            total_validators=len(validators),
            validator_index=validators.index(self.keypair.pubkey()) if self.keypair.pubkey() in validators else None,
            on_finalize_callback=self.on_finalize,
            block_validator=self.validate_block_callback
        )
        
        self.mempool: List[SignedTx] = []
        
        # Register with network
        network.add_node(self)

    def receive(self, message: Message, sim_time: float):
        """Handle incoming messages from the network."""
        # print(f"[Node {self.node_id}] Received {message.msg_type} from {message.from_id}")
        
        if message.msg_type == MessageType.TX:
            tx: SignedTx = message.payload
            if tx not in self.mempool:
                if tx.verify():
                    self.mempool.append(tx)
                    # print(f"[Node {self.node_id}] Added TX to mempool. Size: {len(self.mempool)}")

        elif message.msg_type == MessageType.BLOCK_HEADER:
            # In this simple sim, we treat BLOCK_HEADER as full block for simplicity 
            # or we might need separate types. 
            # Looking at ConsensusEngine, it expects 'block'. 
            # Let's assume payload is the Block object.
            block: Block = message.payload
            
            # Verify signature
            if not block.verify_signature():
                # print(f"[Node {self.node_id}] Invalid block signature")
                return

            vote = self.consensus.on_receive_block(block)
            if vote:
                self.broadcast_vote(vote, sim_time)

        elif message.msg_type == MessageType.VOTE:
            vote = message.payload
            
            # Verify signature
            if not vote.verify():
                # print(f"[Node {self.node_id}] Invalid vote signature")
                return

            vote_response = self.consensus.on_receive_vote(vote)
            if vote_response:
                self.broadcast_vote(vote_response, sim_time)

    def validate_block_callback(self, block: Block) -> bool:
        """Callback for ConsensusEngine to validate a block."""
        # Find parent block
        parent_block = None
        parent_state = self.state # Default to current state (assuming extends tip)
        
        if self.blockchain:
            if block.header.parent_hash == self.blockchain[-1].block_hash():
                parent_block = self.blockchain[-1]
                parent_state = self.state
            else:
                # If it's not extending the tip, we might reject it for this simple sim
                # or we'd need to look back in history.
                # For now, reject forks that are not immediate extensions
                # UNLESS it's genesis (parent_hash all zeros)
                if block.header.height == 0 and not self.blockchain:
                     pass # Genesis case
                else:
                     # print(f"[Node {self.node_id}] Rejecting block {block.header.height} (parent mismatch)")
                     return False
        elif block.header.height > 0:
             # We have no blocks but this is not height 0
             return False

        return validate_block(block, parent_block, parent_state)

    def on_finalize(self, block: Block):
        """Callback when a block is finalized."""
        # print(f"[Node {self.node_id}] Finalized block {block.header.height}: {block.block_hash()}")
        self.blockchain.append(block)
        
        # Update state
        for tx in block.txs:
            self.state.apply_tx(tx)
            # Remove from mempool
            if tx in self.mempool:
                self.mempool.remove(tx)

    def propose_block(self, sim_time: float):
        """Propose a new block if it's our turn."""
        # Check if consensus engine thinks we should propose
        # We need to know current height/round from consensus or track it ourselves.
        # ConsensusEngine tracks current_height and current_round.
        
        height = self.consensus.current_height
        round = self.consensus.current_round
        
        if self.consensus.should_propose(height, round):
            # print(f"[Node {self.node_id}] Proposing block for H={height} R={round}")
            
            parent_block = self.blockchain[-1] if self.blockchain else None
            
            # Build block
            block = build_block(
                parent_block=parent_block,
                parent_state=self.state,
                txs=self.mempool[:], # Include all txs
                keypair=self.keypair
            )
            
            # Feed to own consensus
            vote = self.consensus.on_receive_block(block)
            
            # Broadcast block
            msg = Message(
                msg_id=0, # Network assigns IDs usually? No, Network uses internal seq. Message dataclass has msg_id.
                from_id=self.node_id,
                to_id="BROADCAST", # Network handles broadcast?
                msg_type=MessageType.BLOCK_HEADER, # Using BLOCK_HEADER as BLOCK for now
                payload=block,
                height=height
            )
            
            self.broadcast(msg, sim_time)
            
            if vote:
                self.broadcast_vote(vote, sim_time)

    def broadcast(self, message: Message, sim_time: float):
        """Helper to gossip a message to k random validators instead of broadcasting to all."""
        # Use gossip strategy: send to k random peers instead of all validators
        # This reduces network load while maintaining message propagation
        
        msg = Message(
            msg_id=message.msg_id,
            from_id=self.node_id,
            to_id="GOSSIP",  # Placeholder, will be set by network
            msg_type=message.msg_type,
            payload=message.payload,
            height=message.height
        )
        
        self.network.gossip_send(msg, sim_time, self.gossip_k, exclude_nodes=[self.node_id])

    def broadcast_vote(self, vote, sim_time: float):
        msg = Message(
            msg_id=0,
            from_id=self.node_id,
            to_id="BROADCAST",
            msg_type=MessageType.VOTE,
            payload=vote,
            height=vote.height
        )
        self.broadcast(msg, sim_time)

