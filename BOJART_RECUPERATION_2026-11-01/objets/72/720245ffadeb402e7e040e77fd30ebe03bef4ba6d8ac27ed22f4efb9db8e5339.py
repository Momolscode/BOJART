"""Small MCP stdio client for explicit, local REA investigations."""
import json
import queue
import subprocess
import threading
import time
from pathlib import Path

REA = 'rea'


def evidence(result):
    if result.get('isError'):
        raise RuntimeError(json.dumps(result, ensure_ascii=False)[:5000])
    if result.get('structuredContent') is not None:
        return result['structuredContent']
    for item in result.get('content', []):
        if item.get('type') == 'text':
            try:
                return json.loads(item['text'])
            except json.JSONDecodeError:
                pass
    return result


class ReaClient:
    def __init__(self, directory, command=None):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.q = queue.Queue()
        self.seq = 0
        self.errors = []
        self.p = subprocess.Popen([command or REA, 'mcp'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, bufsize=1)
        def stdout():
            for line in self.p.stdout:
                self.q.put(line)
            self.q.put(None)
        def stderr():
            for line in self.p.stderr:
                self.errors.append(line)
        threading.Thread(target=stdout, daemon=True).start()
        threading.Thread(target=stderr, daemon=True).start()
        self.identity = self.rpc('initialize', {'protocolVersion': '2025-03-26',
                    'capabilities': {}, 'clientInfo': {'name': 'marwin-investigation', 'version': '1.0'}})
        self.rpc('notifications/initialized', {}, notify=True)
        (self.directory / 'server_identity.json').write_text(json.dumps(self.identity, indent=2))

    def rpc(self, method, params, notify=False, timeout=180):
        self.seq += 1
        msg = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notify:
            msg['id'] = self.seq
        self.p.stdin.write(json.dumps(msg) + '\n')
        self.p.stdin.flush()
        if notify:
            return None
        deadline = time.monotonic() + timeout
        while True:
            line = self.q.get(timeout=max(.01, deadline - time.monotonic()))
            if line is None:
                raise RuntimeError('REA closed stdout')
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get('id') != self.seq:
                continue
            if 'error' in r:
                raise RuntimeError(json.dumps(r['error']))
            return r['result']

    def call(self, name, args, label):
        result = self.rpc('tools/call', {'name': name, 'arguments': args})
        p = self.directory / (label + '.json')
        p.write_text(json.dumps({'tool': name, 'arguments': args, 'result': result},
                               ensure_ascii=False, indent=2))
        return evidence(result)

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            self.p.wait(timeout=5)
        (self.directory / 'server_stderr.log').write_text(''.join(self.errors))

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
