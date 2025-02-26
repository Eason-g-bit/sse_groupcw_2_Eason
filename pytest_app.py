import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    if response.status_code == 200:
        assert b'Hello Deepseek' in response.data

def test_register_user(client):
    """test register"""
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Successful registration.' in response.data

def test_register_existing_user(client):
    """Testing the Already Existing User Registration Prompt"""
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
    """test user login"""
    client.post('/register', data={
        'username': 'loginuser',
        'password': 'loginpassword'
    })
    response = client.post('/login', data={
        'username': 'loginuser',
        'password': 'loginpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'chat' in response.data

def test_login_failure(client):
    """Test login failure (wrong username or password)"""
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpassword'
    })
    assert b'The username or password is incorrect, or the user is not registered.' in response.data

def test_chat_access_without_login(client):
    """Test whether accessing the chat page without logging in redirects to the login page"""
    response = client.get('/chat', follow_redirects=True)
    assert response.status_code == 200
    assert b'User Login' in response.data

def test_send_message(client):
    """Testing the ability to send and receive messages with ChatBot"""
    client.post('/register', data={
        'username': 'chatuser',
        'password': 'chatpassword'
    })
    client.post('/login', data={
        'username': 'chatuser',
        'password': 'chatpassword'
    }, follow_redirects=True)

    response = client.post('/send_message', json={'message': 'Hello ChatBot'})
    assert response.status_code == 200
    assert b"ChatBot: I received your message: 'Hello ChatBot'" in response.data
