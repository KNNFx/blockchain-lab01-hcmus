import sys
import os
import argparse
import subprocess

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from node_sim.simulator import Simulator

def run_simulator(config_path, seed, steps, output_file):
    """Run blockchain simulator."""
    sim = Simulator(config_path=config_path, output_file=output_file, seed=seed)
    sim.run(max_steps=steps)

def run_tests():
    """Run all pytest tests."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=False
    )
    return result.returncode

def run_determinism_check():
    """Run determinism check script."""
    script_path = os.path.join(os.path.dirname(__file__), "determinism_test.py")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=False
    )
    return result.returncode

def main():
    parser = argparse.ArgumentParser(
        description="Blockchain Lab - Simulator, Tests, and Determinism Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode simulator                          # Run simulator with default config
  python main.py --mode test                               # Run all tests
  python main.py --mode determinism --seed 42              # Check determinism with seed 42
  python main.py --mode simulator --config config.yaml     # Run with custom config
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["simulator", "test", "determinism"],
        default="simulator",
        help="Execution mode (default: simulator)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default_config.yaml",
        help="Path to config file (for simulator/determinism modes)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for determinism (default: 0)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Max simulation steps"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (for simulator mode; default: stdout)"
    )
    
    args = parser.parse_args()

    if args.mode == "test":
        print("Running all tests...\n")
        exit_code = run_tests()
        sys.exit(exit_code)
    
    elif args.mode == "determinism":
        exit_code = run_determinism_check()
        sys.exit(exit_code)
    
    elif args.mode == "simulator":
        output_file = sys.stdout
        if args.output:
            try:
                output_file = open(args.output, "w")
            except IOError as e:
                print(f"Error opening output file: {e}")
                sys.exit(1)
        
        try:
            run_simulator(args.config, args.seed, args.steps, output_file)
        finally:
            if output_file is not sys.stdout:
                output_file.close()

if __name__ == "__main__":
    main()