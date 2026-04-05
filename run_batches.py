"""
Batch runner for pipeline - runs in smaller chunks so it doesn't timeout.
"""
import subprocess
import sys
import time
import json
from pathlib import Path

def get_lead_count():
    runs = sorted(Path('.cache/runs').glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    if runs:
        return json.loads(runs[0].read_text()).get('lead_count', 0)
    return 0

# Run pipeline with smaller batches
batch_size = 20
total_wanted = 100

for batch in range(5):  # 5 batches of 20 = 100
    current = get_lead_count()
    print(f"Current leads: {current}")
    
    if current >= total_wanted:
        print(f"Reached {current} leads!")
        break
    
    remaining = total_wanted - current
    to_fetch = min(batch_size, remaining)
    
    print(f"Running pipeline to get {to_fetch} more leads...")
    start = time.time()
    
    result = subprocess.run(
        [sys.executable, 'pipeline.py', '--limit', str(to_fetch)],
        capture_output=True,
        timeout=300  # 5 min timeout per batch
    )
    
    elapsed = time.time() - start
    print(f"Batch completed in {elapsed:.0f}s")
    
    new_count = get_lead_count()
    print(f"New lead count: {new_count}")
    
    if new_count == current:
        print("No progress - stopping")
        break

print(f"Final count: {get_lead_count()}")