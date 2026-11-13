"""Real HTTP checks against an already running server; does not use DeepSeek."""
import json
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

root=Path(__file__).resolve().parents[1]
env=dotenv_values(root/'.env')
with httpx.Client(base_url='http://127.0.0.1:8000',headers={'X-Access-Code':env['CAMPUSAI_ACCESS_CODE']},timeout=20,trust_env=False) as c:
    assert c.get('/').status_code==200
    assert c.get('/api/health').json()['status']=='ok'
    with (root/'knowledge/demo/功能演示资料.md').open('rb') as f:
        d=c.post('/api/documents',files={'file':('功能演示资料.md',f)},data={'campus':'通用','source':'本地功能演示资料，非学校通知','category':'其他'}).json()
    assert d['status']=='ready',d
    assert c.get('/api/search',params={'q':'星禾读书会','campus':'保定校区'}).json()
    ident=c.post('/api/chats',json={'campus':'保定校区'}).json()['id']
    started=time.monotonic();timestamps=[];events=[]
    with c.stream('POST',f'/api/chats/{ident}/stream',json={'content':'星禾读书会的活动口令是什么？','campus':'保定校区'}) as response:
        for line in response.iter_lines():
            if line:events.append(json.loads(line));timestamps.append(time.monotonic()-started)
    assert events[-1]['type']=='done'
    history=c.get('/api/chats/'+ident).json()
    assert '青苗向阳' in history[-1]['content'] and history[-1]['sources']
    assert timestamps[-1]-timestamps[1]>.1
    print('HTTP root, health, upload, FTS, references, history: PASS')
    print(f'Incremental stream: {len(events)} events over {timestamps[-1]:.2f}s: PASS')
    # Abort an actual network stream and verify final persistence.
    with c.stream('POST',f'/api/chats/{ident}/stream',json={'content':'星禾读书会','campus':'保定校区'}) as response:
        for line in response.iter_lines():
            if line and json.loads(line)['type']=='delta': break
    time.sleep(.3)
    history=c.get('/api/chats/'+ident).json()
    assert history[-1]['status']=='interrupted',history[-1]
    print('Stop/disconnect partial persistence: PASS')
    c.delete('/api/chats/'+ident)
    c.delete('/api/documents/'+d['id'])
    print('Smoke-test records cleaned; user data preserved.')
