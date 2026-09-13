"""Start run_server.py and exercise real localhost HTTP and WebSocket traffic.

This supplemental smoke test uses loopback networking; it is separate from the
offline graded verifiers that prohibit socket connections. Port 8000 must be free.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent


def run():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    environment = os.environ.copy()
    for key in list(environment):
        if key.upper().endswith('_API_KEY') or key.lower() in {'http_proxy', 'https_proxy', 'all_proxy'}:
            environment.pop(key, None)

    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request('http://127.0.0.1:8000' + path, data=data,
                                     headers={'Content-Type': 'application/json'})
        with opener.open(req, timeout=60) as response:
            return response.status, json.load(response)

    async def websocket_check():
        async with websockets.connect('ws://127.0.0.1:8000/ws/chat/live-ws') as ws:
            await ws.send(json.dumps({'message': 'Check ticket SUP-0014.'}))
            first = json.loads(await ws.recv())
            await ws.send(json.dumps({'message': 'What is its status?'}))
            second = json.loads(await ws.recv())
            assert first['reply']['status'] == 'answered'
            assert second['reply']['memory_used']
            assert second['reply']['resolved_record_id'] == 'SUP-0014'
        return True

    with tempfile.TemporaryFile(mode='w+') as output:
        process = subprocess.Popen([sys.executable, 'run_server.py'], cwd=ROOT,
                                   env=environment, stdout=output, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError('Server exited before becoming ready; check port 8000.')
                try:
                    status, health = request('/health')
                    if status == 200 and health['status'] == 'ok':
                        break
                except (OSError, ValueError):
                    time.sleep(0.5)
            else:
                raise RuntimeError('Server did not start within 60 seconds.')
            # Confirm our process survived binding rather than accepting another server.
            time.sleep(0.2)
            assert process.poll() is None
            _, schema = request('/openapi.json')
            assert '/ask' in schema['paths']
            _, policy = request('/ask', {'session_id': 'live-policy',
                'message': 'How often should outage progress updates be sent?'})
            assert policy['reply']['status'] == 'answered'
            assert policy['review']['approved']
            assert '30' in policy['final_answer']
            _, ticket = request('/ask', {'session_id': 'live-ticket',
                'message': 'Check ticket SUP-0014.'})
            assert ticket['reply']['response']['ticket']['record_id'] == 'SUP-0014'
            _, fallback = request('/ask', {'session_id': 'live-fallback',
                'message': 'What is the weather in Mumbai tomorrow?'})
            assert fallback['reply']['response']['fallback_used']
            assert asyncio.run(websocket_check())
            assert request('/health')[0] == 200
            return {'status': 'PASS', 'actual_server_started': True,
                    'http_policy_ticket_fallback_passed': True,
                    'websocket_memory_and_disconnect_passed': True,
                    'network_scope': 'localhost only; API keys removed',
                    'platform': sys.platform}
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    report = run()
    (ROOT / 'transcripts/live_server_evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
