import pytest
from app import app

@pytest.fixture
def client():
    # 配置 Flask 应用用于测试
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """如果路由改为 / ，可以用这个测试根路径"""
    response = client.get('/')
    # 如果你在 app.py 中将路由改为 @app.route('/')，这个测试就会通过
    if response.status_code == 200:
        assert b'Hello Deepseek' in response.data
