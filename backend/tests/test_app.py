import io
import json
import os
import sys
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import store
from app.main import app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'test.db')
    monkeypatch.setattr(store,'ROOT',tmp_path)
    monkeypatch.setenv('CAMPUSAI_ACCESS_CODE','test-access')
    monkeypatch.setenv('DEEPSEEK_API_KEY','')
    with TestClient(app,headers={'X-Access-Code':'test-access'}) as c: yield c


def upload(client,name,raw,campus='通用'):
    return client.post('/api/documents',files={'file':(name,raw)},data={'campus':campus,'source':'虚构测试资料','category':'校园指南'})


def test_access_and_validation(client):
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/chats',headers={'X-Access-Code':'wrong'}).status_code==401
    assert client.post('/api/chats',json={'campus':'不存在'}).status_code==422
    assert client.post('/api/chats',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert upload(client,'evil.exe',b'bad').status_code==400
    assert upload(client,'huge.txt',b'x'*(10*1024*1024+1)).status_code==413
    assert client.post('/api/settings/test').json()['ok'] is False


def test_upload_search_isolation_delete(client):
    r=upload(client,'../../guide.md','星禾读书会的活动口令是青苗向阳。本文是测试资料。'.encode(), '渤海校区').json()
    assert r['status']=='ready'
    doc=client.get('/api/documents').json()[0]
    assert doc['name']=='guide.md'
    assert len(client.get('/api/search',params={'q':'星禾读书会','campus':'渤海校区'}).json())==1
    assert not client.get('/api/search',params={'q':'星禾读书会','campus':'保定校区'}).json()
    assert '青苗向阳' in client.get('/api/documents/'+r['id']+'/preview').json()['text']
    client.delete('/api/documents/'+r['id'])
    assert not client.get('/api/search',params={'q':'星禾读书会'}).json()
    with store.connection() as c: assert c.execute('SELECT count(*) FROM chunks_fts').fetchone()[0]==0


def test_parsers(client):
    assert upload(client,'测试.txt','校园资料测试文本'.encode('gb18030')).json()['status']=='ready'
    doc=Document();doc.add_paragraph('DOCX campus document text');b=io.BytesIO();doc.save(b)
    assert upload(client,'test.docx',b.getvalue()).json()['status']=='ready'
    # Minimal valid text PDF; exercises extraction independently of a third-party generator.
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream=b'BT /F1 12 Tf 30 100 Td (Campus library document text) Tj ET'
    objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    raw=b'%PDF-1.4\n'; offsets=[0]
    for i,obj in enumerate(objects,1): offsets.append(len(raw));raw+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(raw);raw+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{o:010} 00000 n \n'.encode() for o in offsets[1:])+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    assert upload(client,'text.pdf',raw).json()['status']=='ready'
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);buf=io.BytesIO();writer.write(buf)
    result=upload(client,'scan.pdf',buf.getvalue()).json()
    assert result['status']=='error' and 'OCR' in result['error']


def test_chat_stream_history_regenerate(client):
    upload(client,'demo.md','星禾读书会口令青苗向阳，仅用于测试。'.encode())
    ident=client.post('/api/chats',json={}).json()['id']
    events=[json.loads(line) for line in client.post(f'/api/chats/{ident}/stream',json={'content':'星禾读书会的口令'}).text.splitlines()]
    assert events[0]['type']=='start' and events[0]['sources']
    assert sum(e['type']=='delta' for e in events)>1
    assert events[-1]['type']=='done'
    history=client.get('/api/chats/'+ident).json()
    assert len(history)==2 and '青苗向阳' in history[-1]['content']
    client.post(f'/api/chats/{ident}/stream',json={'content':'刚才的资料来源是什么？'})
    assert len(client.get('/api/chats/'+ident).json())==4
    client.post(f'/api/chats/{ident}/stream',json={'regenerate':True})
    assert len(client.get('/api/chats/'+ident).json())==4
    client.delete('/api/chats/'+ident)
    assert client.get('/api/chats/'+ident).status_code==404


def test_real_ai_contract_with_fake_sdk(client,monkeypatch):
    import app.main as main
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake-test-only')
    monkeypatch.setenv('DEEPSEEK_MODEL','test-model')
    calls=[]
    class Stream:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        def __aiter__(self): return self
        async def __anext__(self):
            if hasattr(self,'sent'): raise StopAsyncIteration
            self.sent=True
            from types import SimpleNamespace as N
            return N(choices=[N(delta=N(content='测试模型返回'))])
    class Fake:
        def __init__(self): self.chat=self;self.completions=self
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def create(self,**kwargs):calls.append(kwargs);return Stream()
    monkeypatch.setattr(main,'client',Fake)
    ident=client.post('/api/chats',json={}).json()['id']
    for q in ['你好','继续说明']:
        assert '测试模型返回' in client.post(f'/api/chats/{ident}/stream',json={'content':q}).text
    assert [m['role'] for m in calls[-1]['messages']]==['system','user','assistant','user']
    assert calls[-1]['stream'] is True
    # Real network calls are intentionally not claimed by this SDK contract test.
