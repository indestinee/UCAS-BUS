# http://docs.jinkan.org/docs/flask/quickstart.html#quickstart
from flask import Flask, render_template, session, \
        redirect, url_for, escape, request, Response
import re, argparse, os, pickle, time
from order import Order
from hash_table import hash_func

def get_web_args():# {{{
    parser = argparse.ArgumentParser(description='bus ticket')
    parser.add_argument('--public', action='store_true', default=False)
    parser.add_argument('--port', default=1234, type=int)
    args = parser.parse_args()
    return args
# }}}
daydayday = ['Monday', 'Tuesday', 'Wednesday', \
        'Thursday', 'Friday', 'Saturday', 'Sunday']

def get_date(delta=0):# {{{
    t = time.localtime(time.time() + delta * 86400)
    s = '%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    day = t.tm_wday
    return [s, '%s %s' % (s, daydayday[day])]
# }}}

args = get_web_args()
app = Flask(__name__, static_folder='static', static_url_path='/static')
users_save_file = './data'


users_path = './data/'
users = os.listdir(users_path)
hash_table = {hash_func(user): user for user in users}
limit = 10
cnt = {user: 0 for user in users}
obj = {}

if not args.public:
    hash_table['123'] = hash_table[hash_func(users[-1])]

with open('user_information.txt', 'w') as f:
    for key, value in hash_table.items():
        f.write('%s: %s\n' % (value, key))

def main():
    mine = obj[session['id']]
    data = {
        'template_name_or_list': 'main.html',
        'username': session['username'],
        'cnt': cnt[session['username']],
    }
        
    data['status'] = session['status']
    if session['status'] == 0:
        if request.method == 'POST':
            certcode = request.form['certcode']
            res = mine.login(certcode)
            if res:
                session['status'] += 1
                return redirect(url_for('index'))
            else:
                data['msg'] = '[ERR] wrong certcode!'
        path = mine.get_certcode()
        data['certcode_path'] = path
        data['current'] = '[LOG] enter certcode and login in payment'

    elif session['status'] == 1:
        if request.method == 'POST':
            date = request.form['date']
            session['date'] = date.split('|')
            session['status'] += 1
            return redirect(url_for('index'))

        data['msg'] = ['[SUC] login succeed!']
        dates = [['0', 'please select the date']] + \
                [get_date(i) for i in range(4)]
        data['dates'] = dates
        data['current'] = '[LOG] select date'
        
    elif session['status'] == 2:
        if request.method == 'POST':
            route = request.form['route']
            session['route'] = route.split('|')
            session['status'] += 1
            return redirect(url_for('index'))

        data['msg'] = ['[LOG] select date: ' + session['date'][-1]]
        raw_route_list = mine.get_route(session['date'][0])
        route_list = [['0', 'please select your route']] + \
                [[route['routecode'], 'name: {}, time: {}, code: {}'\
                .format(route['routename'], route['routetime'],\
                route['routecode'])] for route in raw_route_list]
        data['route_list'] = route_list
        data['current'] = '[LOG] select route'

    elif session['status'] == 3:
        if request.method == 'POST':
            wait = request.form['wait']
            session['wait'] = wait
            session['status'] += 1
            return redirect(url_for('index'))
        data['current'] = '[LOG] choose one of the following two buttons and press!'
        data['msg'] = ['[LOG] select date: ' + session['date'][-1],\
                '[LOG] select route: ' + session['route'][-1]]
    elif session['status'] == 4:
        wait = int(session['wait'])
        if wait == 1:
            if 'time' not in session:
                res = mine.calc_time()
                session['time'] = res
            
            cur = time.time()
            data['msg'] = ['[WRN] DO NOT login too early before system opens, there may be a time limit for COOCKIES!']
            if cur > session['time']:
                session['wait'] = '0'
                session['status'] += 1
                redirect(url_for('index'))
            delta = int(session['time'] - cur)
            data['delta'] = delta
            data['fresh'] = max(1, delta//3)
        else:
            session['status'] += 1
            data['delta'] = 1
            data['fresh'] = 1
            redirect(url_for('index'))

    elif session['status'] == 5:
        result, data['msg'] = mine.buy(session)
        if result:
            session['status'] += 1
        redirect(url_for('index'))
    elif session['status'] == 6:
        data['wechat'] = mine.wechat
        data['msg'] = ['[SUC] please scan the QRcode with wechat']
    else:
        data['msg'] = ['[ERR] no such status']
    return render_template(**data)

def login(username=None):
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
        obj[session['id']] = Order(username, session['id'])
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

@app.route('/previous')
def previous():
    if session['status'] > 1:
        session['status'] -= 1
    return redirect(url_for('index'))

@app.route('/restart')
def restart():
    session['status'] = min(session['status'], 1)
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return main()
    return login()

@app.route('/login/<string:username>')
def _login(username=None):
    return login(username)


if __name__ == '__main__':
    host = '0.0.0.0' if args.public else '127.0.0.1'
    app.secret_key = os.urandom(32)
    app.run(host=host, port=args.port, debug=True if not args.public else False)
