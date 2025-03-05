from flask import Flask, request, jsonify, render_template, Response
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
import jwt
import datetime
import psutil
from openai import OpenAI
import threading

app = Flask(__name__)

# Supabase 配置
url = "https://ofxbmmidmnqpuueyncqu.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9meGJtbWlkbW5xcHV1ZXluY3F1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA4NjEwMjYsImV4cCI6MjA1NjQzNzAyNn0.qo7L6egD7Tl3l4lUOq8WnfwX2aL3Vuvec4UapZFBxbA"
client = create_client(url, key)

SECRET_KEY = '2096f222f081e53ba68b0a77df1291759027c2dbc1214caf379892ea5455688f'


# **ChatBot 类（DeepSeek API）**
# class ChatBot:
#     def __init__(self):
#         self.client = OpenAI(api_key="sk-qN8gLbSZOJoxFw8eB7642bEdE5Af43BeBb6035A4BcDa7061",
#                              base_url="http://maas-api.cn-huabei-1.xf-yun.com/v1")
#         self.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

#     def add_message(self, message):
#         self.conversation_history.extend(message)

#     def chat(self, message, model="xdeepseekv3"):
#         self.add_message(message)
#         try:
#             response = self.client.chat.completions.create(
#                 model=model,
#                 messages=self.conversation_history,
#                 temperature=0.7,
#                 max_tokens=150,
#                 extra_headers={"lora_id": "0"}
#             )

#             assistant_message = response.choices[0].message.content
#             self.conversation_history.append({"role": "assistant", "content": assistant_message})
#             return assistant_message
#         except Exception as e:
#             return f"Error: {e}"
## 支持流响应
class ChatBot:
    def __init__(self):
        self.client = OpenAI(api_key="sk-qN8gLbSZOJoxFw8eB7642bEdE5Af43BeBb6035A4BcDa7061",
                             base_url="http://maas-api.cn-huabei-1.xf-yun.com/v1")
        self.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

    def add_message(self, message):
        self.conversation_history.extend(message)

    def chat(self, message, model="xdeepseekv3", stream=False):
        self.add_message(message)
        try:
            if stream:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"},
                    stream=True,
                    stream_options={"include_usage": True}
                )

                for chunk in response:
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        # print("this is chat: ", chunk_content)
                        yield chunk_content  # 仅流式返回每个块

                # # Once streaming is done, append the final assistant message to the conversation history
                # self.conversation_history.append({"role": "assistant", "content": assistant_message})

                # # Return the final assistant message (this will be the last chunk)
                # return assistant_message  # 完整消息（最后）


            else:
                # 普通响应
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"}
                )

                assistant_message = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                return assistant_message  # 返回完整的消息
        except Exception as e:
            return f"Error: {e}"


def is_system_under_high_load():
    # 判断 CPU 或内存使用率来确定是否为高负载
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    return cpu_usage > 80 or memory_usage > 80  # 可根据需要调整阈值


# 减少token消耗
def combine_message(message, updated_messages):
    print(updated_messages)
    conversation_history = [{"role": msg["role"], "content": msg["content"]}
                            for msg in updated_messages['messages']]
    conversation_history.append({"role": "user", "content": message})
    return conversation_history


# 异步架构处理database
def update_database(updated_messages, message, assistant_message, conversation):
    """ 更新数据库的异步函数 """
    updated_messages['messages'].append(
        {"role": "user", "content": message, "timestamp": datetime.datetime.now().isoformat()})
    updated_messages['messages'].append(
        {"role": "assistant", "content": assistant_message, "timestamp": datetime.datetime.now().isoformat()})

    # 存入数据库
    client.table('chat_history').update({
        "messages": updated_messages, "updated_at": datetime.datetime.now().isoformat()
    }).eq('id', conversation.data[0]['id']).execute()

    print("数据库更新完毕")


@app.route('/')
def index():
    return render_template('SPA.html')


# **用户注册**
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']

    if username == '':
        return jsonify({"message": "Please input username"}), 400
    elif password == '':
        return jsonify({"message": "Please input password"}), 400

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

    if username == '':
        return jsonify({"message": "Please input username"}), 400
    elif password == '':
        return jsonify({"message": "Please input password"}), 400

    user = client.table('users').select('*').eq('username', username).execute()

    if user.data and check_password_hash(user.data[0]['password'], password):
        token = jwt.encode(
            {'user_id': user.data[0]['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            SECRET_KEY, algorithm="HS256")
        return jsonify({"token": token})
    else:
        return jsonify({"message": "Invalid username or password"}), 401


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
            messages = conversation.data[0].get('messages', {}).get('messages', [])
            return jsonify({"messages": messages}), 200  # ✅ 确保返回的是列表
        else:
            return jsonify({"messages": []}), 200
    except Exception as e:
        print(f"Error in chat_history: {e}")  # ✅ 记录错误日志
        return jsonify({"message": "Internal Server Error"}), 500


# **发送消息**
# @app.route('/api/send_message', methods=['POST'])
# def send_message():
#     token = request.headers.get('Authorization').split(" ")[1]
#     data = request.get_json()
#     message = data['message']
#     chat_name = data.get("chat_name", "Default Chat")  # 确保获取 chat_name

#     try:
#         decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         user_id = decoded_token['user_id']

#         # **查找当前 chat_name 是否存在**
#         conversation = client.table('chat_history').select('*').eq('user_id', user_id).eq('name', chat_name).execute()

#         if not conversation.data:
#             return jsonify({"message": "Chat not found"}), 404

#         # **更新消息**
#         updated_messages = conversation.data[0]['messages']
#         conversation_history = combine_message(message, updated_messages)
#         chatbot = ChatBot()
#         assistant_message = chatbot.chat(conversation_history)
#         updated_messages['messages'].append(
#             {"role": "user", "message": message, "timestamp": datetime.datetime.now().isoformat()})
#         updated_messages['messages'].append(
#             {"role": "assistant", "message": assistant_message, "timestamp": datetime.datetime.now().isoformat()})

#         # **存入数据库**
#         client.table('chat_history').update({
#             "messages": updated_messages, "updated_at": datetime.datetime.now().isoformat()
#         }).eq('id', conversation.data[0]['id']).execute()

#         return jsonify({"message": assistant_message}), 200
#     except jwt.ExpiredSignatureError:
#         return jsonify({"message": "Token expired"}), 401
#     except jwt.InvalidTokenError:
#         return jsonify({"message": "Invalid token"}), 401

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

        if not conversation.data:
            return jsonify({"message": "Chat not found"}), 404

        updated_messages = conversation.data[0]['messages']
        conversation_history = combine_message(message, updated_messages)
        # print(conversation_history)

        chatbot = ChatBot()

        # 根据负载选择是否使用流式响应
        if is_system_under_high_load():  ## 检查负载
            print(1)
            # 高负载时使用普通响应
            assistant_message = chatbot.chat(conversation_history, stream=False)
            update_database(updated_messages, message, assistant_message, conversation)
            return jsonify({"message": assistant_message}), 200
        else:
            # 低负载：流式
            print(2)
            assistant_message = ""  # 用于拼接整段DeepSeek输出

            def generate():
                nonlocal assistant_message
                for chunk in chatbot.chat(conversation_history, stream=True):
                    # print("this is flask: ", chunk)
                    assistant_message += chunk  # 每拿到一块就累加
                    yield chunk  # 实时发给前端

                # 流结束后 => assistant_message是完整回复
                update_database(updated_messages, message, assistant_message, conversation)

            return Response(generate(), content_type='text/plain;charset=utf-8')


    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

# **删除特定聊天**
@app.route('/api/delete_chat', methods=['POST'])
def delete_chat():
    token = request.headers.get('Authorization').split(" ")[1]
    data = request.get_json()
    chat_name = data.get('chat_name')

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # **检查该聊天是否存在**
        conversation = client.table('chat_history').select('*').eq('user_id', user_id).eq('name', chat_name).execute()

        if not conversation.data:
            return jsonify({"message": "Chat not found"}), 404

        # **删除该聊天**
        client.table('chat_history').delete().eq('user_id', user_id).eq('name', chat_name).execute()

        return jsonify({"message": "Chat deleted successfully"}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

if __name__ == '__main__':
    app.run(debug=True)