import yaml

class Simulator:
    def __init__(self, network, nodes, config_path="config/config.yaml"):
        self.network = network
        self.nodes = nodes
        self.load_config(config_path)

    def load_config(self, path):
        with open(path, "r") as f:
            self.config = yaml.safe_load(f)
        print(f"Loaded config: {self.config}")

    def tick(self):
        # Mock tick: broadcast a test message from first node
        if self.nodes:
            self.network.broadcast(self.nodes[0], {"type": "TICK", "data": "simulation step"})

    def run(self, max_steps=None):
        print("Starting simulation...")
        # Use provided max_steps or fall back to config, or default to a safe limit
        limit = max_steps if max_steps is not None else self.config["simulation"].get("max_blocks", 100)
        
        step = 0
        while True:
            step += 1
            print(f"--- Step {step} ---")
            self.tick()
            
            # Allow nodes to process
            for node in self.nodes:
                # Simple round-robin proposal for testing
                if step % 2 == 0:
                    node.propose_block()

            # Check termination
            if step >= limit:
                print("Simulation ended (max steps reached).")
                break