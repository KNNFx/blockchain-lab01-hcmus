import sys
import os
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from node_sim.simulator import Simulator

def main():
    parser = argparse.ArgumentParser(description="Blockchain Simulator")
    parser.add_argument("--config", type=str, default="config/default_config.yaml", help="Path to config file")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for determinism")
    parser.add_argument("--steps", type=int, default=None, help="Max simulation steps")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: stdout)")
    
    args = parser.parse_args()

    output_file = sys.stdout
    if args.output:
        try:
            output_file = open(args.output, "w")
        except IOError as e:
            print(f"Error opening output file: {e}")
            sys.exit(1)

    try:
        sim = Simulator(config_path=args.config, output_file=output_file, seed=args.seed)
        sim.run(max_steps=args.steps)
    finally:
        if output_file is not sys.stdout:
            output_file.close()

if __name__ == "__main__":
    main()