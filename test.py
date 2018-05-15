from flask import Flask, session
import os

app = Flask(__name__)
app.secret_key = os.urandom(32)

session(app)

@app.route('/set/')
def set():
    session['key'] = 'value'
    return 'ok'

@app.route('/get/')
def get():
    return session.get('key', 'not set')

@app.route('/')
def index():
    return 'index'

if __name__ == '__main__':
    app.run(debug=True)
