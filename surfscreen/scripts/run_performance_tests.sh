#!/bin/bash
###############################################################################
# Performance Tests Runner
# 
# Load testing and performance benchmarks for SurfScreen.
# Uses all 36 CPUs for parallel stress testing.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_outputs/performance"
PERF_LOG="$TEST_OUTPUT_DIR/perf_results_$(date +%Y%m%d_%H%M%S).log"

# Get number of CPUs
NUM_CPUS=$(nproc 2>/dev/null || echo 36)

echo "=================================================="
echo "PERFORMANCE TESTS"
echo "=================================================="
echo "CPUs: $NUM_CPUS"
echo "Output: $PERF_LOG"
echo ""

cd "$PROJECT_ROOT"
mkdir -p "$TEST_OUTPUT_DIR"

# Initialize log
echo "Performance Test Results - $(date)" > "$PERF_LOG"
echo "======================================" >> "$PERF_LOG"
echo "" >> "$PERF_LOG"

# ============================================
# 1. Module Import Time Benchmark
# ============================================
echo "--- 1. Module Import Time ---" | tee -a "$PERF_LOG"

python << 'EOF' | tee -a "$PERF_LOG"
import time
import sys

modules = [
    'surfscreen',
    'surfscreen.core',
    'surfscreen.api',
    'surfscreen.analysis',
    'surfscreen.cache',
    'surfscreen.batch',
    'surfscreen.scheduler',
    'surfscreen.auth',
    'surfscreen.notifications',
]

print(f"{'Module':<40} {'Time (ms)':<10}")
print("-" * 50)

total_time = 0
for module in modules:
    try:
        # Clear from cache
        for key in list(sys.modules.keys()):
            if key.startswith('surfscreen'):
                del sys.modules[key]
        
        start = time.perf_counter()
        __import__(module)
        elapsed = (time.perf_counter() - start) * 1000
        total_time += elapsed
        print(f"{module:<40} {elapsed:>8.2f}")
    except ImportError as e:
        print(f"{module:<40} SKIP ({e})")

print("-" * 50)
print(f"{'Total':<40} {total_time:>8.2f}")
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# 2. API Response Time Benchmark
# ============================================
echo "--- 2. API Response Time ---" | tee -a "$PERF_LOG"

python << 'EOF' | tee -a "$PERF_LOG"
import time
import statistics

try:
    from surfscreen.api.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    endpoints = [
        ('GET', '/'),
        ('GET', '/health'),
        ('GET', '/api/v1/jobs'),
        ('GET', '/api/v1/cache/stats'),
    ]
    
    print(f"{'Endpoint':<30} {'Avg (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10}")
    print("-" * 60)
    
    for method, path in endpoints:
        times = []
        
        # Warm up
        for _ in range(5):
            try:
                if method == 'GET':
                    client.get(path)
            except:
                pass
        
        # Benchmark
        for _ in range(100):
            try:
                start = time.perf_counter()
                if method == 'GET':
                    response = client.get(path)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            except:
                pass
        
        if times:
            avg = statistics.mean(times)
            p95 = sorted(times)[int(len(times) * 0.95)]
            p99 = sorted(times)[int(len(times) * 0.99)]
            print(f"{method} {path:<26} {avg:>8.2f} {p95:>10.2f} {p99:>10.2f}")
        else:
            print(f"{method} {path:<26} SKIP")
    
except Exception as e:
    print(f"API benchmark failed: {e}")
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# 3. Parallel Processing Benchmark
# ============================================
echo "--- 3. Parallel Processing Benchmark (${NUM_CPUS} CPUs) ---" | tee -a "$PERF_LOG"

python << EOF | tee -a "$PERF_LOG"
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import math

NUM_CPUS = $NUM_CPUS

def cpu_bound_task(n):
    """CPU-intensive task."""
    total = 0
    for i in range(n):
        total += math.sqrt(i) * math.sin(i)
    return total

def run_benchmark(executor_class, name, num_workers, num_tasks, task_size):
    start = time.perf_counter()
    with executor_class(max_workers=num_workers) as executor:
        results = list(executor.map(cpu_bound_task, [task_size] * num_tasks))
    elapsed = time.perf_counter() - start
    throughput = num_tasks / elapsed
    return elapsed, throughput

print(f"{'Test':<40} {'Time (s)':<10} {'Throughput':<15}")
print("-" * 65)

# Process pool tests
for workers in [4, 16, NUM_CPUS]:
    name = f"ProcessPool ({workers} workers)"
    elapsed, throughput = run_benchmark(ProcessPoolExecutor, name, workers, 100, 100000)
    print(f"{name:<40} {elapsed:>8.2f} {throughput:>12.1f} tasks/s")

# Thread pool tests
for workers in [4, 16, NUM_CPUS]:
    name = f"ThreadPool ({workers} workers)"
    elapsed, throughput = run_benchmark(ThreadPoolExecutor, name, workers, 100, 10000)
    print(f"{name:<40} {elapsed:>8.2f} {throughput:>12.1f} tasks/s")

print(f"\nOptimal workers for CPU-bound: {NUM_CPUS}")
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# 4. Memory Usage Test
# ============================================
echo "--- 4. Memory Usage Test ---" | tee -a "$PERF_LOG"

python << 'EOF' | tee -a "$PERF_LOG"
import sys
import gc
import tracemalloc

# Start memory tracking
tracemalloc.start()

print("Memory usage by module:")
print("-" * 50)

modules_to_test = [
    ('surfscreen.core', None),
    ('surfscreen.api.main', 'app'),
    ('surfscreen.cache', 'CacheManager'),
    ('surfscreen.batch', 'BatchProcessor'),
]

for module_name, obj_name in modules_to_test:
    gc.collect()
    before = tracemalloc.get_traced_memory()[0]
    
    try:
        module = __import__(module_name, fromlist=[obj_name] if obj_name else [])
        if obj_name:
            obj = getattr(module, obj_name, None)
        
        after = tracemalloc.get_traced_memory()[0]
        diff = (after - before) / 1024 / 1024
        print(f"{module_name:<40} {diff:>8.2f} MB")
    except Exception as e:
        print(f"{module_name:<40} SKIP ({e})")

current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print("-" * 50)
print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# 5. File I/O Benchmark
# ============================================
echo "--- 5. File I/O Benchmark ---" | tee -a "$PERF_LOG"

python << 'EOF' | tee -a "$PERF_LOG"
import tempfile
import time
import os
import json

print(f"{'Operation':<40} {'Time (ms)':<10} {'Speed':<15}")
print("-" * 65)

# JSON serialization
data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(10000)]}

start = time.perf_counter()
json_str = json.dumps(data)
elapsed = (time.perf_counter() - start) * 1000
size_kb = len(json_str) / 1024
print(f"JSON serialize (10k items)              {elapsed:>8.2f} {size_kb:.1f} KB")

start = time.perf_counter()
_ = json.loads(json_str)
elapsed = (time.perf_counter() - start) * 1000
print(f"JSON deserialize (10k items)            {elapsed:>8.2f}")

# File write/read
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
    temp_path = f.name
    
    start = time.perf_counter()
    f.write(json_str)
    f.flush()
    os.fsync(f.fileno())
    elapsed = (time.perf_counter() - start) * 1000
    print(f"File write ({size_kb:.1f} KB)                  {elapsed:>8.2f} {size_kb/elapsed*1000:.1f} KB/s")

start = time.perf_counter()
with open(temp_path, 'r') as f:
    _ = f.read()
elapsed = (time.perf_counter() - start) * 1000
print(f"File read ({size_kb:.1f} KB)                   {elapsed:>8.2f} {size_kb/elapsed*1000:.1f} KB/s")

os.unlink(temp_path)
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# 6. Stress Test Summary
# ============================================
echo "--- 6. System Stress Test ---" | tee -a "$PERF_LOG"

python << EOF | tee -a "$PERF_LOG"
import os
import platform
import psutil

print("System Information:")
print("-" * 50)
print(f"Platform: {platform.platform()}")
print(f"Python: {platform.python_version()}")
print(f"CPU Count: {os.cpu_count()}")
print(f"Total Memory: {psutil.virtual_memory().total / 1e9:.1f} GB")
print(f"Available Memory: {psutil.virtual_memory().available / 1e9:.1f} GB")
print(f"Disk Usage: {psutil.disk_usage('/').percent}%")

# Load averages (Linux only)
try:
    load1, load5, load15 = os.getloadavg()
    print(f"Load Average: {load1:.2f}, {load5:.2f}, {load15:.2f}")
except:
    pass
EOF

echo "" | tee -a "$PERF_LOG"

# ============================================
# Summary
# ============================================
echo "=================================================="
echo "PERFORMANCE TEST COMPLETE"
echo "=================================================="
echo "Results saved to: $PERF_LOG"
echo ""

cat "$PERF_LOG"
