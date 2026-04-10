import subprocess
import time
import os
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_INTERVAL = 10

def git_pull():
    result = subprocess.run(["git", "pull", "--ff-only"], cwd=REPO_DIR, capture_output=True, text=True)
    return "Already up to date" not in result.stdout

def run_bot():
    return subprocess.Popen([sys.executable, "bot.py"], cwd=REPO_DIR)

if __name__ == "__main__":
    print("=== HAMASHA BOT AUTO-UPDATER ===")
    print(f"Checking GitHub every {CHECK_INTERVAL}s...")
    proc = run_bot()
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            if git_pull():
                print("[UPDATE] New version found, restarting...")
                proc.terminate()
                proc.wait(timeout=5)
                proc = run_bot()
        except Exception as e:
            print(f"[ERROR] {e}")
