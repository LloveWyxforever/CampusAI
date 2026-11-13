"""Use the real SDK with a local mock transport; never contact or bill DeepSeek."""
import json
import httpx
from openai import AsyncOpenAI

from test_app import client


def test_configuration_and_key_not_exposed(client,monkeypatch):
    import app.main as main
    monkeypatch.setenv('DEEPSEEK_API_KEY','   ')
    assert main.settings()['configured'] is False
    monkeypatch.setenv('DEEPSEEK_API_KEY','  local-test-secret  ')
    monkeypatch.setenv('DEEPSEEK_BASE_URL',' https://api.deepseek.com ')
    monkeypatch.setenv('DEEPSEEK_MODEL',' model-from-list ')
    result=client.get('/api/settings')
    assert 'local-test-secret' not in result.text
    assert result.json()['model']=='model-from-list'
    assert result.json()['base_url']=='https://api.deepseek.com'
    ai=main.client()
    assert ai.api_key=='local-test-secret'
    assert str(ai.base_url)=='https://api.deepseek.com'


def test_sdk_http_stream_and_connection_test(client,monkeypatch):
    import app.main as main
    monkeypatch.setenv('DEEPSEEK_API_KEY','local-test-secret')
    monkeypatch.setenv('DEEPSEEK_MODEL','model-from-list')
    requests=[]
    def handle(request):
        requests.append(request)
        assert request.headers['authorization']=='Bearer local-test-secret'
        if request.url.path=='/models':
            return httpx.Response(200,json={'object':'list','data':[{'id':'model-from-list','object':'model','created':0,'owned_by':'test'}]})
        assert request.url.path=='/chat/completions'
        body=json.loads(request.content)
        assert body['model']=='model-from-list'
        if body.get('stream'):
            chunks=[{'id':'test','object':'chat.completion.chunk','created':0,'model':'model-from-list','choices':[{'index':0,'delta':{'content':part},'finish_reason':None}]} for part in ['SDK流式','回答测试']]
            return httpx.Response(200,headers={'content-type':'text/event-stream'},content=''.join('data: '+json.dumps(c,ensure_ascii=False)+'\n\n' for c in chunks)+'data: [DONE]\n\n')
        return httpx.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'model-from-list','choices':[{'index':0,'message':{'role':'assistant','content':'连接测试（模拟）'},'finish_reason':'stop'}]})
    def sdk_client():
        return AsyncOpenAI(api_key='local-test-secret',base_url='https://api.deepseek.com',http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),max_retries=0)
    monkeypatch.setattr(main,'client',sdk_client)
    assert client.post('/api/settings/test').json()['ok'] is True
    ident=client.post('/api/chats',json={}).json()['id']
    result=client.post(f'/api/chats/{ident}/stream',json={'content':'你好'})
    events=[json.loads(line) for line in result.text.splitlines()]
    assert ''.join(e['content'] for e in events if e['type']=='delta')=='SDK流式回答测试'
    assert events[-1]['type']=='done'
    assert '资料摘录模式' not in result.text
    assert 'local-test-secret' not in result.text
    assert client.get('/api/chats/'+ident).json()[-1]['content']=='SDK流式回答测试'


def test_configured_api_failure_does_not_fall_back_to_demo(client,monkeypatch):
    import app.main as main
    monkeypatch.setenv('DEEPSEEK_API_KEY','local-test-secret')
    monkeypatch.setenv('DEEPSEEK_MODEL','model-from-list')
    def handle(request):
        return httpx.Response(401,json={'error':{'message':'invalid key','type':'authentication_error'}})
    monkeypatch.setattr(main,'client',lambda:AsyncOpenAI(api_key='local-test-secret',base_url='https://api.deepseek.com',http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),max_retries=0))
    result=client.post('/api/settings/test').json()
    assert result['ok'] is False and '认证失败' in result['message']
    ident=client.post('/api/chats',json={}).json()['id']
    response=client.post(f'/api/chats/{ident}/stream',json={'content':'你好'})
    assert '认证失败' in response.text
    assert '资料摘录模式' not in response.text
    assert client.get('/api/chats/'+ident).json()[-1]['status']=='error'
