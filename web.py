# http://docs.jinkan.org/docs/flask/quickstart.html#quickstart
from flask import Flask, render_template, session, \
        redirect, url_for, escape, request, Response
import re, argparse, os, pickle, time
from order import Order
from hash_table import hash_func
import numpy as np
def get_current_time():
    _date = time.localtime(time.time())
    current_time = '%d-%02d-%02d %02d:%02d:%02d' % (\
        _date.tm_year, _date.tm_mon, _date.tm_mday, \
        _date.tm_hour, _date.tm_min, _date.tm_sec)
    return current_time

limit = 100
users_path = './data/'
daydayday = ['星期' + each for each in '一二三四五六日']

def get_web_args():# {{{
    parser = argparse.ArgumentParser(description='bus ticket')
    parser.add_argument('--public', action='store_true', default=False)
    parser.add_argument('--port', default=1234, type=int)
    args = parser.parse_args()
    return args
# }}}
def get_date(delta=0):# {{{
    t = time.localtime(time.time() + delta * 86400)
    s = '%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    day = t.tm_wday
    return [s, '%s %s' % (s, daydayday[day])]
# }}}

args = get_web_args()
app = Flask(__name__, static_folder='static', static_url_path='/static')

users = os.listdir(users_path)
hash2user = {hash_func(user): user for user in users}
cnt = {user: 0 for user in users}
id2obj = {}
user2id = {user: set() for user in users}

if not args.public:
    hash2user['123'] = hash2user[hash_func(users[-1])]

with open('user_information.txt', 'w') as f:
    for key, value in hash2user.items():
        f.write('%s: %s\n' % (value, key))

def main():
    try:
        my_obj = id2obj[session['id']]
        # return logout()
    except:
        return login()

    data = {
        'template_name_or_list': 'main.html',
        'username': session['username'],
        'cnt': cnt[session['username']],
    }
    data['status'] = session['status']
    if session['status'] == 0:# {{{
        if request.method == 'POST':
            certcode = request.form['certcode']
            res = my_obj.login(certcode)
            if res:
                session['status'] += 1
                return redirect(url_for('index'))
            else:
                data['msg'] = ['[ERR] wrong certcode!']
        path = my_obj.get_certcode()
        data['certcode_path'] = path
        data['current'] = 'enter certcode and login in payment'
# }}}
    elif session['status'] == 1:# {{{
        if request.method == 'POST':
            date = request.form['date']
            session['cache'] = True if 'cache' in request.form else False
            session['date'] = date.split('|')
            session['status'] += 1
            return redirect(url_for('index'))

        data['msg'] = ['[SUC] login succeed!']
        dates = [get_date(i) + [''] for i in range(5)]
        dates[3][2] = 'checked'
        data['dates'] = dates
        
        data['current'] = 'select date'
    # }}}
    elif session['status'] == 2:# {{{
        if request.method == 'POST':
            route = request.form['route']
            session['route'] = route.split('|')
            session['status'] += 1
            return redirect(url_for('index'))

        data['current'] = 'select route'

        data['msg'] = ['[LOG] select date: ' + session['date'][-1]]
        try:
            raw_route_list = my_obj.get_route(session['date'][0], \
                    session['cache'])
        except:
            data['msg'] += ['[ERR] connot get route! something wrong with either ucas server or this server!']
            data['route_list'] = [['0', '[ERR] connot get route! something wrong with either ucas server or this server!', 'disabled']]
            return render_template(**data)
        
        route_list = [[route['routecode'], 'name: {}, time: {}, code: {}'\
                .format(route['routename'], route['routetime'],\
                route['routecode']), ''] for route in raw_route_list]

        def mark_favorite(favorite):
            for each in route_list:
                if favorite in each[1] and '助教' not in each[1]:
                    each[2] = 'checked'
                    return True

        for each in route_list:
            if '助教' in each[1]:
                each[2] = 'disabled'

        if not mark_favorite('玉泉路—雁栖湖18:00'):
            mark_favorite('雁栖湖—玉泉路13:00')
        data['route_list'] = route_list
        
# }}}
    elif session['status'] == 3:# {{{
        if request.method == 'POST':
            wait = request.form['time']
            session['wait'] = wait
            session['status'] += 1
            return redirect(url_for('index'))

        data['current'] = 'choose order time'
        def get_next_18_time():
            cur = (time.time() + 8 * 3600) % 86400 / 3600 
            return get_date(1 if cur >= 18 else 0)
        _date = time.localtime(time.time())
        h, m = _date.tm_hour, _date.tm_min

        data['t1'], data['t2'] = '', ''
        if h >= 18 and h <= 18:
            data['t1'] = 'checked'
        else:
            data['t2'] = 'checked'
        next_18_time = get_next_18_time()[0] + ' 18:00:00'

        current_time = get_current_time()
        data['s1'] = 'start now ' + current_time
        data['s2'] = 'start at  ' + next_18_time
        data['msg'] = ['[LOG] select date: ' + session['date'][-1],\
                '[LOG] select route: ' + session['route'][-1]]
        data['msg'] += ['[WRN] DO NOT login too early before system opens, there may be a time limit for COOCKIES!']
# }}}
    elif session['status'] == 4:# {{{
        wait = int(session['wait'])
        if wait == 1:
            if 'time' not in session:
                res = my_obj.calc_time()
                session['time'] = res
            data['current'] = 'please wait ...'
            cur = time.time()
            data['msg'] = ['[WRN] DO NOT login too early before system opens, there may be a time limit for COOCKIES!']
            if cur > session['time']:
                session['status'] += 1
                session['attemps'] = 0
                return redirect(url_for('index'))
            delta = int(session['time'] - cur)
            data['fresh'] = max(1, delta//3)
            eta = ''
            if delta > 3600:
                eta += '%dh '%(delta//3600)
                delta %= 3600
            if delta > 60:
                eta += '%dm '%(delta//60)
                delta %= 60
            eta += '%ds'%delta
            data['cur_time'] = get_current_time()
            data['eta'] = eta
        else:
            session['status'] += 1
            session['attemps'] = 0
            return redirect(url_for('index'))
# }}}
    elif session['status'] == 5:# {{{
        session['attemps'] += 1
        data['current'] = 'sending order information [%d]...' % \
                session['attemps']
        result, data['msg'] = my_obj.buy(session)
        data['fresh'] = np.random.uniform(1.0, 2.0)

        if result:
            session['status'] += 1
            redirect(url_for('index'))
# }}}
    elif session['status'] == 6:# {{{
        data['current'] = 'succeed'
        data['wechat'] = my_obj.wechat
        data['msg'] = ['[SUC] ordered successfully!', \
                '[LOG] please scan the QRcode with wechat']
# }}}
    else:# {{{
        data['msg'] = ['[ERR] no such status']
# }}}
    return render_template(**data)

def login(username=None):
    if request.method == 'POST':
        username = request.form['username']
    if username in hash2user:
        username = hash2user[username]

        if cnt[username] == limit:
            return render_template('login.html', **{'msg': 'Login limit!'})
        cnt[username] += 1

        session['username'] = username
        session['id'] = '{}{}'.format(username, time.time())
        session['status'] = 0   #init
        user2id[username].add(session['id'])
        id2obj[session['id']] = Order(username, session['id'])
        return redirect(url_for('index'))
    else:
        data = {'msg': 'Error, no such code in data base!' if username \
                else 'Please enter your code to log in!'}
        return render_template('login.html', **data)

@app.route('/logout')# {{{
def logout():
    try:
        id2obj.pop(session['id'])
        cnt[session['username']] -= 1
        session.clear()
    except:
        pass
    return redirect(url_for('index'))
# }}}

@app.route('/undo')# {{{
def undo():
    try:
        if session['status'] >= 5:
            session['status'] = 3
        elif session['status'] > 1:
            session['status'] -= 1
    except:
        pass
    return redirect(url_for('index'))
# }}}
@app.route('/refresh')# {{{
def refresh():
    return redirect(url_for('index'))
# }}}
@app.route('/logout_all')# {{{
def logout_all():
    try:
        username = session['username']
        for identifier in user2id[username]:
            id2obj.pop(identifier)
        cnt[username] = 0
    except:
        pass
    return redirect(url_for('index'))
# }}}
@app.route('/restart')# {{{
def restart():
    try:
        session['status'] = min(session['status'], 1)
    except:
        pass
    return redirect(url_for('index'))
# }}}
@app.route('/', methods=['GET', 'POST'])# {{{
def index():
    if 'username' in session:
        return main()
    return login()
# }}}
@app.route('/login/<string:username>')# {{{
def _login(username=None):
    logout()
    return login(username)
# }}}

if __name__ == '__main__':
    host = '0.0.0.0' if args.public else '127.0.0.1'
    app.secret_key = os.urandom(32)
    app.run(host=host, port=args.port, debug=True if not args.public else False)
