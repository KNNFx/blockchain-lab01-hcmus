from typing import List, Optional
import binascii

from network.network import Node as NetworkNode
from network.messages import Message, MessageType
from consensus.consensus import ConsensusEngine
from blocklayer.block import Block, build_block, validate_block
from blocklayer.ledger import Ledger
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
        
        # Initialize Ledger to manage blocks and states
        self.ledger = Ledger()
        
        # For backward compatibility, keep references to current state
        self.state = State() # Genesis state
        
        # Initialize Consensus Engine
        self.consensus = ConsensusEngine(
            validator_keypair=self.keypair,
            total_validators=len(validators),
            validator_index=validators.index(self.keypair.pubkey()) if self.keypair.pubkey() in validators else None,
            on_finalize_callback=self.on_finalize,
            on_ask_for_block=self.request_missing_block,
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
        
        elif message.msg_type == MessageType.GET_BLOCK:
            # Another node is requesting a block by hash
            block_hash = message.payload
            self.handle_block_request(block_hash, message.from_id, sim_time)
        
        elif message.msg_type == MessageType.BLOCK_BODY:
            # Received a block in response to our GET_BLOCK request
            block: Block = message.payload
            
            # Verify signature
            if not block.verify_signature():
                return
            
            # Feed to consensus (it will check if this is the missing block)
            vote = self.consensus.on_receive_block(block)
            if vote:
                self.broadcast_vote(vote, sim_time)

    def validate_block_callback(self, block: Block) -> bool:
        """Callback for ConsensusEngine to validate a block."""
        # Get latest finalized block and state from ledger
        latest = self.ledger.latest_finalized()
        
        if latest:
            parent_block, parent_state = latest
            # Check if this block extends the current tip
            if block.header.parent_hash == parent_block.block_hash():
                return validate_block(block, parent_block, parent_state)
            else:
                # For simplicity, reject forks that don't extend the tip
                return False
        else:
            # No blocks yet - this should be genesis (height 0)
            if block.header.height == 0:
                return validate_block(block, None, State())
            else:
                return False

    def on_finalize(self, block: Block):
        """Callback when a block is finalized."""
        # print(f"[Node {self.node_id}] Finalized block {block.header.height}: {block.block_hash()}")
        
        # Apply transactions to create new state
        new_state = State()
        
        # Start from parent state if exists
        latest = self.ledger.latest_finalized()
        if latest:
            _, parent_state = latest
            new_state = State()
            # Copy parent state data
            for key, value in parent_state.data.items():
                new_state.data[key] = value
        
        # Apply all transactions in this block
        for tx in block.txs:
            new_state.apply_tx(tx)
            # Remove from mempool
            if tx in self.mempool:
                self.mempool.remove(tx)
        
        # Add block and its resulting state to ledger
        self.ledger.add_block(block, new_state)
        
        # Update current state reference for backward compatibility
        self.state = new_state

    def propose_block(self, sim_time: float):
        """Propose a new block if it's our turn."""
        # Check if consensus engine thinks we should propose
        # We need to know current height/round from consensus or track it ourselves.
        # ConsensusEngine tracks current_height and current_round.
        
        height = self.consensus.current_height
        round = self.consensus.current_round
        
        if self.consensus.should_propose(height, round):
            # print(f"[Node {self.node_id[:8]}] Proposing block for H={height} R={round}")
            
            # Get parent block and state from ledger
            latest = self.ledger.latest_finalized()
            if latest:
                parent_block, parent_state = latest
            else:
                parent_block = None
                parent_state = State()
            
            # Build block
            block = build_block(
                parent_block=parent_block,
                parent_state=parent_state,
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
    
    def request_missing_block(self, block_hash: str):
        """
        Callback được gọi bởi ConsensusEngine khi thiếu block data.
        Broadcast GET_BLOCK request để yêu cầu peers gửi block.
        """
        # In a real system, we might track which peers likely have the block
        # For simplicity, broadcast to all via gossip
        # Note: sim_time is not available here, using 0.0 as placeholder
        # The network will use current simulation time anyway
        msg = Message(
            msg_id=0,
            from_id=self.node_id,
            to_id="BROADCAST",
            msg_type=MessageType.GET_BLOCK,
            payload=block_hash,
            height=None
        )
        # Use gossip to request from multiple peers
        self.network.gossip_send(msg, 0.0, self.gossip_k, exclude_nodes=[self.node_id])
    
    def handle_block_request(self, block_hash: str, requester_id: str, sim_time: float):
        """
        Handle GET_BLOCK request from another node.
        Send BLOCK_BODY response if we have the block.
        """
        # Check if we have this block in our ledger
        # Search through all heights
        for height in self.ledger.blocks.keys():
            block = self.ledger.blocks[height]
            if block.block_hash() == block_hash:
                # Found the block, send it back
                msg = Message(
                    msg_id=0,
                    from_id=self.node_id,
                    to_id=requester_id,
                    msg_type=MessageType.BLOCK_BODY,
                    payload=block,
                    height=block.header.height
                )
                # Send directly to requester (not gossip)
                self.network.send(msg, sim_time)
                return
        
        # Block not found - do nothing (requester will timeout or retry)
    
    @property
    def blockchain(self) -> List[Block]:
        """
        Backward compatibility property to get list of blocks.
        Returns blocks sorted by height.
        """
        if not self.ledger.blocks:
            return []
        heights = sorted(self.ledger.blocks.keys())
        return [self.ledger.blocks[h] for h in heights]

