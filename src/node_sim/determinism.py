import subprocess
import os
import sys
import filecmp
def run_simulation(output_file):
    """Runs the simulation and writes stdout to output_file."""
    print(f"Running simulation, outputting to {output_file}...")
    with open(output_file, "w") as f:
        # Assuming src/main.py is the entry point and we run from project root
        result = subprocess.run(
            [sys.executable, "src/main.py"],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd() # Ensure we run from current directory
        )
        if result.returncode != 0:
            print(f"Error running simulation: {result.stderr}")
            return False
    return True
def main():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log1 = os.path.join(log_dir, "run_1.log")
    log2 = os.path.join(log_dir, "run_2.log")
    # Run 1
    if not run_simulation(log1):
        sys.exit(1)
    # Run 2
    if not run_simulation(log2):
        sys.exit(1)
    # Compare
    print("Comparing logs...")
    if filecmp.cmp(log1, log2, shallow=False):
        print("Determinism check passed: Logs are identical.")
    else:
        print("Determinism check FAILED: Logs differ.")
        # Optional: Print diff
        with open(log1, 'r') as f1, open(log2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            import difflib
            diff = difflib.unified_diff(lines1, lines2, fromfile='run_1.log', tofile='run_2.log')
            for line in diff:
                print(line, end='')
        sys.exit(1)
if __name__ == "__main__":
    main()