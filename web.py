# http://docs.jinkan.org/docs/flask/quickstart.html#quickstart
from flask import Flask, render_template, session, \
        redirect, url_for, escape, request
import re, argparse, os, pickle, hashlib, time
from bus import Order

def get_web_args():# {{{
    parser = argparse.ArgumentParser(description='bus ticket')
    parser.add_argument('--public', action='store_true', default=False)
    parser.add_argument('--port', default=1234, type=int)
    args = parser.parse_args()
    return args
# }}}

args = get_web_args()
app = Flask(__name__)
users_save_file = './data'

def hash_func(user):# {{{
    salt = 'aksdjocijnewqkjdcis893sa'
    func = hashlib.sha512()
    func.update((user + salt).encode(encoding='utf-8'))
    return func.hexdigest()
# }}}
users_path = './data/'
users = os.listdir(users_path)
hash_table = {hash_func(user): user for user in users}
limit = 10
cnt = {user: 0 for user in users}
obj = {}

if not args.public:
    hash_table['123'] = hash_table[hash_func(users[1])]

with open('user_information.txt', 'w') as f:
    for key, value in hash_table.items():
        f.write('%s: %s\n' % (value, key))


def main():
    data = {
        'template_name_or_list': 'main.html',
        'username': session['username'],
        'cnt': cnt[session['username']],
    }
        
    if session['status'] == 0:
        pass
    elif session['status'] == 1:
        pass
    else:
        pass

    session['status'] += 1
    return render_template(**data)

def login(username):
    if request.method == 'POST':
        username = request.form['username']
    if username in hash_table:
        username = hash_table[username]
        if cnt[username] == limit:
            return render_template('login.html', **{'msg': 'login limit!'})
        cnt[username] += 1
        session['username'] = username
        session['id'] = '{}{}'.format(username, time.time())
        session['status'] = 0
        obj[session['id']] = Order(username)
        return redirect(url_for('index'))
    else:
        data = {
            'msg': 'Please login with your code first!' \
                    if username == None else \
                    ('This code \'%s\' matches nobody!' % username)
        }
        return render_template('login.html', **data)
    
@app.route('/logout')
def logout():
    cnt[session['username']] -= 1
    session.pop('username')
    obj.pop(session['id'])
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
@app.route('/<username>')
def index(username=None):
    if 'username' in session:
        return main()
    return login(username)




if __name__ == '__main__':
    host = '0.0.0.0' if args.public else '127.0.0.1'
    app.secret_key = os.urandom(32)
    app.run(host=host, port=args.port, debug=True)
