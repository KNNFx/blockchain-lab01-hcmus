import subprocess
import os
import sys
import filecmp
import hashlib

def run_simulation(output_file):
    """Runs the simulation and writes stdout to output_file."""
    print(f"Running simulation, outputting to {output_file}...")
    with open(output_file, "w") as f:
        result = subprocess.run(
            [sys.executable, "src/main.py"],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        if result.returncode != 0:
            print(f"Error running simulation: {result.stderr}")
            return False
    return True

def compare_files_byte_by_byte(file1, file2):
    """Compares two files byte by byte."""
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        while True:
            b1 = f1.read(4096)
            b2 = f2.read(4096)
            if b1 != b2:
                return False
            if not b1:
                return True

def get_file_hash(filepath):
    """Calculates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log1 = os.path.join(log_dir, "run_1.log")
    log2 = os.path.join(log_dir, "run_2.log")
    report_file = os.path.join(log_dir, "run_compare.txt")

    # Run 1
    if not run_simulation(log1):
        sys.exit(1)

    # Run 2
    if not run_simulation(log2):
        sys.exit(1)

    print("Comparing logs...")
    
    # Byte-by-byte comparison
    is_identical = compare_files_byte_by_byte(log1, log2)
    
    # Hash comparison (Mocking state hash check by hashing the log file)
    hash1 = get_file_hash(log1)
    hash2 = get_file_hash(log2)
    
    result_msg = ""
    if is_identical and hash1 == hash2:
        result_msg = "Determinism check passed: Logs are identical byte-by-byte."
        print(result_msg)
    else:
        result_msg = "Determinism check FAILED: Logs differ."
        print(result_msg)

    # Write report
    with open(report_file, "w") as f:
        f.write("Determinism Check Report\n")
        f.write("========================\n")
        f.write(f"Run 1 Hash: {hash1}\n")
        f.write(f"Run 2 Hash: {hash2}\n")
        f.write(f"Result: {result_msg}\n")
    print(f"Report written to {report_file}")

    if not is_identical:
        sys.exit(1)

if __name__ == "__main__":
    main()
