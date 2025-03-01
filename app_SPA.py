from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
import jwt
import datetime
from openai import OpenAI

app = Flask(__name__)

# Supabase 配置
url = "https://ofxbmmidmnqpuueyncqu.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9meGJtbWlkbW5xcHV1ZXluY3F1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA4NjEwMjYsImV4cCI6MjA1NjQzNzAyNn0.qo7L6egD7Tl3l4lUOq8WnfwX2aL3Vuvec4UapZFBxbA"
client = create_client(url, key)

SECRET_KEY = '2096f222f081e53ba68b0a77df1291759027c2dbc1214caf379892ea5455688f'


# **ChatBot 类（GPT API）**
class ChatBot:
    def __init__(self):
        self.client = OpenAI(api_key="sk-qN8gLbSZOJoxFw8eB7642bEdE5Af43BeBb6035A4BcDa7061",
                             base_url="http://maas-api.cn-huabei-1.xf-yun.com/v1")
        self.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

    def add_message(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    def clear_history(self):
        self.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

    def chat(self, message, model="xdeepseekv3"):
        self.add_message("user", message)
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=150,
                extra_headers={"lora_id": "0"}
            )

            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            return f"Error: {e}"


@app.route('/')
def index():
    return render_template('SPA.html')


# **用户注册**
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = client.table('users').select('*').eq('username', username).execute()
    if user.data:
        return jsonify({"message": "Username already taken"}), 400

    hashed_password = generate_password_hash(password)
    client.table('users').insert({"username": username, "password": hashed_password}).execute()

    return jsonify({"message": "Registration successful"}), 201


# **用户登录**
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = client.table('users').select('*').eq('username', username).execute()

    if user.data and check_password_hash(user.data[0]['password'], password):
        token = jwt.encode(
            {'user_id': user.data[0]['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            SECRET_KEY, algorithm="HS256")
        return jsonify({"token": token})
    else:
        return jsonify({"message": "Invalid credentials"}), 401


# **创建新聊天**
@app.route('/api/start_chat', methods=['POST'])
def start_chat():
    token = request.headers.get('Authorization').split(" ")[1]
    data = request.get_json()
    chat_name = data.get('chat_name', 'Untitled Chat')

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # 检查是否已经有同名 chat 存在
        existing_chat = client.table('chat_history').select('*').eq('user_id', user_id).eq('name', chat_name).execute()

        if existing_chat.data:
            return jsonify({"message": "Chat already exists", "chat_name": chat_name}), 200

        # **创建新 chat，初始无消息**
        client.table('chat_history').insert({
            "user_id": user_id,
            "name": chat_name,
            "messages": {"messages": []},  # 空的对话历史
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
        }).execute()

        return jsonify({"message": "Chat started", "chat_name": chat_name}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401



# **获取聊天历史列表**
@app.route('/api/chat_list', methods=['GET'])
def chat_list():
    token = request.headers.get('Authorization').split(" ")[1]

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        conversations = client.table('chat_history').select("name").eq('user_id', user_id).execute()

        return jsonify({"chats": [conv["name"] for conv in conversations.data]}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


# **获取特定聊天记录**
@app.route('/api/chat_history', methods=['GET'])
def chat_history():
    token = request.headers.get('Authorization').split(" ")[1]
    chat_name = request.args.get('chat_name', '')  # ✅ 从查询参数获取 chat_name

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # ✅ 检查 chat_name 是否为空
        if not chat_name:
            return jsonify({"message": "Chat name is required"}), 400

        # ✅ 查找该用户的指定聊天记录
        conversation = client.table('chat_history').select('*').eq('user_id', user_id).eq('name', chat_name).execute()

        if conversation.data:
            return jsonify({"messages": conversation.data[0]['messages']['messages']}), 200
        else:
            return jsonify({"messages": []}), 200
    except Exception as e:
        print(f"Error in chat_history: {e}")  # ✅ 记录错误日志
        return jsonify({"message": "Internal Server Error"}), 500




# **发送消息**
@app.route('/api/send_message', methods=['POST'])
def send_message():
    token = request.headers.get('Authorization').split(" ")[1]
    data = request.get_json()
    message = data['message']
    chat_name = data.get("chat_name", "Default Chat")  # 确保获取 chat_name

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # **查找当前 chat_name 是否存在**
        conversation = client.table('chat_history').select('*').eq('user_id', user_id).eq('name', chat_name).execute()

        chatbot = ChatBot()
        assistant_message = chatbot.chat(message)

        if not conversation.data:
            return jsonify({"message": "Chat not found"}), 404

        # **更新消息**
        updated_messages = conversation.data[0]['messages']
        updated_messages['messages'].append(
            {"sender": "user", "message": message, "timestamp": datetime.datetime.now().isoformat()})
        updated_messages['messages'].append(
            {"sender": "assistant", "message": assistant_message, "timestamp": datetime.datetime.now().isoformat()})

        # **存入数据库**
        client.table('chat_history').update({
            "messages": updated_messages, "updated_at": datetime.datetime.now().isoformat()
        }).eq('id', conversation.data[0]['id']).execute()

        return jsonify({"message": assistant_message}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401



if __name__ == '__main__':
    app.run(debug=True)