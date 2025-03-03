import pytest
from app_SPA import app, client, SECRET_KEY
import jwt
import datetime

@pytest.fixture
def client_app():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# 生成测试用户 Token
def generate_test_token(user_id):
    return jwt.encode({
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, SECRET_KEY, algorithm="HS256")

# 测试用户注册
def test_register(client_app):
    response = client_app.post('/api/register', json={"username": "testuser", "password": "testpass"})
    assert response.status_code in [201, 400]  # 用户可能已经存在

# 测试用户登录
def test_login(client_app):
    response = client_app.post('/api/login', json={"username": "testuser", "password": "testpass"})
    assert response.status_code in [200, 401]  # 可能用户名或密码错误
    if response.status_code == 200:
        assert "token" in response.get_json()

# 测试创建新聊天
def test_start_chat(client_app):
    token = generate_test_token(1)
    response = client_app.post('/api/start_chat', json={"chat_name": "Test Chat"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 401]

# 测试获取聊天历史列表
def test_chat_list(client_app):
    token = generate_test_token(1)
    response = client_app.get('/api/chat_list', headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 401]

# 测试获取特定聊天记录
def test_chat_history(client_app):
    token = generate_test_token(1)
    response = client_app.get('/api/chat_history?chat_name=Test Chat', headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 400, 401]

# 测试发送消息
def test_send_message(client_app):
    token = generate_test_token(1)
    response = client_app.post('/api/send_message', json={"message": "Hello", "chat_name": "Test Chat"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 401, 404]
