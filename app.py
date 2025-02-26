from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'supersecretkey'

users_db = {}
chat_history = {}
chat_records = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users_db and users_db[username] == password:
            session['username'] = username
            return redirect(url_for('function_page'))
        else:
            error = "The username or password is incorrect, or the user is not registered."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users_db:
            error = "Username already exists, please select another username."
        else:
            users_db[username] = password
            success = "Successful registration."
    return render_template('register.html', error=error, success=success)

@app.route('/function')
def function_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('function.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/start_chat', methods=['POST'])
def start_chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    chat_name = request.json.get('chat_name')
    username = session['username']
    chat_history.setdefault(username, []).append(chat_name)
    chat_records.setdefault((username, chat_name), [])
    return jsonify({'redirect_url': url_for('chat', chat_name=chat_name)})

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user_history = chat_history.get(username, [])
    return render_template('history.html', history=user_history)

@app.route('/chat')
def chat():
    if 'username' in session:
        chat_name = request.args.get('chat_name', 'Default Chat')
        username = session['username']
        messages = chat_records.get((username, chat_name), [])
        return render_template('chat.html', username=username, chat_name=chat_name, messages=messages)
    return redirect(url_for('login'))

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')
    chat_name = request.json.get('chat_name')
    username = session['username']

    chat_records.setdefault((username, chat_name), []).append({'sender': 'user', 'text': user_message})

    reply = f"ChatBot: I received your message: '{user_message}'"
    chat_records[(username, chat_name)].append({'sender': 'bot', 'text': reply})
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(debug=True)