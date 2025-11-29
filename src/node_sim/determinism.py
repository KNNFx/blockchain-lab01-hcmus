import subprocess
import os
import sys
import filecmp
import hashlib

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

def calculate_file_hash(filepath):
    """Calculates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def main():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log1 = os.path.join(log_dir, "run_1.log")
    log2 = os.path.join(log_dir, "run_2.log")
    compare_file = os.path.join(log_dir, "run_compare.txt")

    # Run 1
    if not run_simulation(log1):
        sys.exit(1)
        
    # Run 2
    if not run_simulation(log2):
        sys.exit(1)

    # Compare
    print("Comparing logs...")
    
    is_identical = filecmp.cmp(log1, log2, shallow=False)
    
    hash1 = calculate_file_hash(log1)
    hash2 = calculate_file_hash(log2)

    with open(compare_file, "w") as f:
        f.write(f"Run 1 Hash: {hash1}\n")
        f.write(f"Run 2 Hash: {hash2}\n")
        if is_identical:
            f.write("Determinism check passed: Logs are identical.\n")
            print("Determinism check passed: Logs are identical.")
        else:
            f.write("Determinism check FAILED: Logs differ.\n")
            print("Determinism check FAILED: Logs differ.")
            
            # Optional: Print diff to compare file
            with open(log1, 'r') as f1, open(log2, 'r') as f2:
                lines1 = f1.readlines()
                lines2 = f2.readlines()
                import difflib
                diff = difflib.unified_diff(lines1, lines2, fromfile='run_1.log', tofile='run_2.log')
                for line in diff:
                    f.write(line)
    
    if not is_identical:
        sys.exit(1)

if __name__ == "__main__":
    main()