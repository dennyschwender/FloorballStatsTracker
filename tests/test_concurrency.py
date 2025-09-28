import threading
import time

from app import app


def _make_requests(worker_id, results):
    try:
        with app.test_client() as c:
            # mark authenticated
            with c.session_transaction() as s:
                s['authenticated'] = True
            rv1 = c.get('/')
            rv2 = c.get('/stats')
            results[worker_id] = (rv1.status_code, rv2.status_code)
    except Exception as e:
        results[worker_id] = e


def test_concurrent_requests_smoke():
    threads = []
    results = {}
    n = 8
    for i in range(n):
        t = threading.Thread(target=_make_requests, args=(i, results))
        threads.append(t)
        t.start()
        time.sleep(0.02)  # slight stagger
    for t in threads:
        t.join()

    for k, v in results.items():
        assert not isinstance(v, Exception)
        assert v[0] == 200 and v[1] == 200
