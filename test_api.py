import requests
import time
import json

results = []
for i in range(10):
    start = time.time()
    try:
        r = requests.post('http://localhost:5000/api/complete',
            json={'code': 'def hello():'},
            headers={'X-API-Key': 'test-key'},
            timeout=5)
        latency = (time.time() - start) * 1000
        results.append({'request': i, 'latency_ms': latency, 'status': r.status_code})
        print(f'Request {i}: {latency:.2f}ms')
    except Exception as e:
        print(f'Request {i}: ERROR - {e}')

with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('✅ Results saved to results.json')
