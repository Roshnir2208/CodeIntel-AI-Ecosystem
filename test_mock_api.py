import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

results = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'latencies': [],
    'errors': []
}

def send_request(i):
    try:
        start = time.time()
        r = requests.post('http://localhost:5000/api/complete',
            json={'code': 'def hello():\n    pass'},
            headers={'X-API-Key': 'test-key'},
            timeout=30)  # Increase timeout to 30s
        latency = (time.time() - start) * 1000
        return {'success': True, 'latency': latency, 'status': r.status_code}
    except Exception as e:
        return {'success': False, 'error': str(e)}

print("Starting load test (10 requests, 2 workers)...")
print("⏳ First request will download model (~500MB), please wait...")
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(send_request, i) for i in range(10)]
    for future in as_completed(futures):
        result = future.result()
        results['total_requests'] += 1
        if result['success']:
            results['successful_requests'] += 1
            results['latencies'].append(result['latency'])
            print(f"✅ Request {results['total_requests']}: {result['latency']:.2f}ms (Status: {result['status']})")
        else:
            results['failed_requests'] += 1
            results['errors'].append(result['error'])
            print(f"❌ Request {results['total_requests']}: {result['error']}")

if results['latencies']:
    results['avg_latency'] = sum(results['latencies']) / len(results['latencies'])
    results['min_latency'] = min(results['latencies'])
    results['max_latency'] = max(results['latencies'])

with open('load_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "="*50)
print(f"Total: {results['total_requests']} | Success: {results['successful_requests']} | Failed: {results['failed_requests']}")
if results['latencies']:
    print(f"Avg Latency: {results['avg_latency']:.2f}ms")
    print(f"Min/Max: {results['min_latency']:.2f}ms / {results['max_latency']:.2f}ms")
print("="*50)
print("✅ Results saved to load_results.json")
