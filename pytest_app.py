import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hello Deepseek' in response.data

def test_register_user(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Successful registration.' in response.data

def test_register_existing_user(client):
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword'
    })
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'newpassword'
    })
    assert b'Username already exists, please select another username.' in response.data

def test_login_success(client):
    client.post('/register', data={
        'username': 'loginuser',
        'password': 'loginpassword'
    })
    response = client.post('/login', data={
        'username': 'loginuser',
        'password': 'loginpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Function Page' in response.data

def test_login_failure(client):
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpassword'
    })
    assert b'The username or password is incorrect, or the user is not registered.' in response.data

def test_chat_access_without_login(client):
    response = client.get('/chat', follow_redirects=True)
    assert response.status_code == 200
    assert b'User Login' in response.data

def test_start_chat(client):
    """测试用例 test_start_chat 解析 JSON 响应并检查 redirect_url 字段"""
    client.post('/register', data={
        'username': 'chatuser',
        'password': 'chatpassword'
    })
    client.post('/login', data={
        'username': 'chatuser',
        'password': 'chatpassword'
    }, follow_redirects=True)
    response = client.post('/start_chat', json={'chat_name': 'Test Chat'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['redirect_url'] == '/chat?chat_name=Test+Chat'

def test_chat_history(client):
    client.post('/register', data={
        'username': 'historyuser',
        'password': 'historypassword'
    })
    client.post('/login', data={
        'username': 'historyuser',
        'password': 'historypassword'
    }, follow_redirects=True)
    client.post('/start_chat', json={'chat_name': 'History Chat'})
    response = client.get('/history')
    assert b'History Chat' in response.data

def test_send_message(client):
    client.post('/register', data={
        'username': 'messageuser',
        'password': 'messagepassword'
    })
    client.post('/login', data={
        'username': 'messageuser',
        'password': 'messagepassword'
    }, follow_redirects=True)
    client.post('/start_chat', json={'chat_name': 'Message Chat'})

    response = client.post('/send_message', json={
        'message': 'Hello ChatBot',
        'chat_name': 'Message Chat'
    })
    assert response.status_code == 200
    assert b"ChatBot: I received your message: 'Hello ChatBot'" in response.data

def test_return_function_page(client):
    client.post('/register', data={
        'username': 'returnuser',
        'password': 'returnpassword'
    })
    client.post('/login', data={
        'username': 'returnuser',
        'password': 'returnpassword'
    }, follow_redirects=True)
    client.post('/start_chat', json={'chat_name': 'Return Chat'})

    response = client.get('/function')
    assert response.status_code == 200
    assert b'Function Page' in response.data