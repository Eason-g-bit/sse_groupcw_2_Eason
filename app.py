from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'supersecretkey'

users_db = {}

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
            return redirect(url_for('chat'))
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

@app.route('/chat')
def chat():
    if 'username' in session:
        return render_template('chat.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')
    reply = f"ChatBot: I received your message: '{user_message}'"
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(debug=True)