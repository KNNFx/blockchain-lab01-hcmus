import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from node_sim.simulator import Simulator

def main():
    config_path = "config/default_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    # Simulator now initializes everything internally
    sim = Simulator(config_path=config_path, output_file=sys.stdout)
    sim.run()

if __name__ == "__main__":
    main()