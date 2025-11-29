import yaml
import sys
import random
from typing import List

from network.network import Network
from network.logging_utils import JsonLinesLogger
from node_sim.node import Node
from core.crypto_layer import KeyPair

class Simulator:
    def __init__(self, config_path="config/config.yaml", output_file=sys.stdout, seed=0):
        self.config = {}
        self.load_config(config_path)
        
        # Initialize RNG
        self.rng = random.Random(seed)
        
        # Initialize Logger
        self.logger = JsonLinesLogger(output_file)
        
        # Initialize Network
        self.network = Network(
            logger=self.logger,
            rng=self.rng,
            min_delay=self.config["simulation"].get("min_delay", 0.1),
            max_delay=self.config["simulation"].get("max_delay", 0.5),
            drop_prob=self.config["simulation"].get("drop_prob", 0.0),
            dup_prob=self.config["simulation"].get("dup_prob", 0.0)
        )
        
        # Initialize Nodes
        num_nodes = self.config["simulation"].get("num_nodes", 4)
        self.nodes: List[Node] = []
        self.validators: List[str] = []
        
        # Generate keys deterministically
        keypairs = []
        for _ in range(num_nodes):
            # KeyPair expects 32 bytes seed
            kp_seed = self.rng.randbytes(32)
            keypairs.append(KeyPair(seed=kp_seed))
            
        self.validators = [kp.pubkey() for kp in keypairs]
        
        for i in range(num_nodes):
            node_id = self.validators[i] # Use pubkey as node_id for simplicity
            node = Node(
                node_id=node_id,
                network=self.network,
                keypair=keypairs[i],
                validators=self.validators
            )
            self.nodes.append(node)

    def load_config(self, path):
        try:
            with open(path, "r") as f:
                self.config = yaml.safe_load(f)
            # print(f"Loaded config: {self.config}")
        except FileNotFoundError:
            print(f"Config file not found at {path}, using defaults.")
            self.config = {"simulation": {"num_nodes": 4, "max_blocks": 10}}

    def run(self, max_steps=None):
        print("Starting simulation...")
        limit = max_steps if max_steps is not None else self.config.get("simulation", {}).get("max_blocks", 100)
        
        current_time = 0.0
        last_proposal_time = 0.0
        proposal_interval = 1.0 # Try to propose every 1 second
        
        finalized_count = 0
        
        while True:
            # 1. Deliver next event
            next_event_time = self.network.deliver_next()
            
            if next_event_time:
                current_time = next_event_time
            else:
                # No events, advance time
                current_time += 0.1
            
            # 2. Trigger block proposal periodically
            if current_time - last_proposal_time >= proposal_interval:
                for node in self.nodes:
                    node.propose_block(current_time)
                last_proposal_time = current_time
            
            # 3. Check termination condition
import yaml
import sys
import random
from typing import List

from network.network import Network
from network.logging_utils import JsonLinesLogger
from node_sim.node import Node
from core.crypto_layer import KeyPair

class Simulator:
    def __init__(self, config_path="config/config.yaml", output_file=sys.stdout, seed=0):
        self.config = {}
        self.load_config(config_path)
        
        # Initialize RNG
        self.rng = random.Random(seed)
        
        # Initialize Logger
        self.logger = JsonLinesLogger(output_file)
        
        # Initialize Network
        self.network = Network(
            logger=self.logger,
            rng=self.rng,
            min_delay=self.config["simulation"].get("min_delay", 0.1),
            max_delay=self.config["simulation"].get("max_delay", 0.5),
            drop_prob=self.config["simulation"].get("drop_prob", 0.0),
            dup_prob=self.config["simulation"].get("dup_prob", 0.0)
        )
        
        # Initialize Nodes
        num_nodes = self.config["simulation"].get("num_nodes", 4)
        self.nodes: List[Node] = []
        self.validators: List[str] = []
        
        # Generate keys deterministically
        keypairs = []
        for _ in range(num_nodes):
            # KeyPair expects 32 bytes seed
            kp_seed = self.rng.randbytes(32)
            keypairs.append(KeyPair(seed=kp_seed))
            
        self.validators = [kp.pubkey() for kp in keypairs]
        
        for i in range(num_nodes):
            node_id = self.validators[i] # Use pubkey as node_id for simplicity
            node = Node(
                node_id=node_id,
                network=self.network,
                keypair=keypairs[i],
                validators=self.validators
            )
            self.nodes.append(node)

    def load_config(self, path):
        try:
            with open(path, "r") as f:
                self.config = yaml.safe_load(f)
            # print(f"Loaded config: {self.config}")
        except FileNotFoundError:
            print(f"Config file not found at {path}, using defaults.")
            self.config = {"simulation": {"num_nodes": 4, "max_blocks": 10}}

    def run(self, max_steps=None):
        print("Starting simulation...")
        limit = max_steps if max_steps is not None else self.config.get("simulation", {}).get("max_blocks", 100)
        
        current_time = 0.0
        last_proposal_time = 0.0
        proposal_interval = 1.0 # Try to propose every 1 second
        
        finalized_count = 0
        
        while True:
            # 1. Deliver next event
            next_event_time = self.network.deliver_next()
            
            if next_event_time:
                current_time = next_event_time
            else:
                # No events, advance time
                current_time += 0.1
            
            # 2. Trigger block proposal periodically
            if current_time - last_proposal_time >= proposal_interval:
                for node in self.nodes:
                    node.propose_block(current_time)
                last_proposal_time = current_time
            
            # 3. Check termination condition
            # Check max height among nodes
            max_height = 0
            for node in self.nodes:
                if node.blockchain:
                    max_height = max(max_height, node.blockchain[-1].header.height)
            
            if max_height >= limit:
                print(f"Simulation ended (max height {max_height} reached).")
                self._print_final_states()
                break
                
            # Safety break to prevent infinite loops if stuck
            if current_time > 1000:
                print("Simulation ended (timeout).")
                self._print_final_states()
                break

    def _print_final_states(self):
        print("\n=== Final State Hashes ===")
        for node in self.nodes:
            state_hash = node.state.commitment().hex()
            print(f"Node {node.node_id}: {state_hash} (Height: {len(node.blockchain)})")