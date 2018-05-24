from flask import Flask, render_template, session, \
        redirect, url_for, escape, request, Response
import re, argparse, os, pickle, time, json
import numpy as np

from order import Order
from hash_table import hash_func
from certcode.raw_data import recognition
from log import Log 


def get_current_time(ns=False):# {{{
    _date = time.localtime(time.time())
    current_time = '%d-%02d-%02d %02d:%02d:%02d' % (\
        _date.tm_year, _date.tm_mon, _date.tm_mday, \
        _date.tm_hour, _date.tm_min, _date.tm_sec)
    
    return current_time if not ns else (current_time + (' %f' % (time.time() % 1)))
# }}}

limit = 100
users_path = './data/'
daydayday = ['星期' + each for each in '一二三四五六日']
last_operate = get_current_time()
running = os.path.isfile('running.status')
ip_count = {}

try:
    import cv2
    max_attemps_recognition = 2
    pattern = np.array(\
            [cv2.imread('certcode/%d.png'%i, 0) for i in range(10)])
    pattern = pattern.reshape(10, -1).transpose()
except:
    max_attemps_recognition = 0

def auto_recognition_attemps(my_obj):
    name = ''
    msg = '[LOG] auto recognition not used!'
    for i in range(max_attemps_recognition):
        path = my_obj.get_certcode()
        path = os.path.join('static', path)
        img = cv2.imread(path, 1)
        certcode = recognition(img, pattern)
        s = '%d%d%d%d'%(certcode[0], certcode[1], certcode[2], certcode[3])
        res, name, msg = my_obj.login(s)
        if res:
            return res, name, msg
    return False, name, msg

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
log = Log('./log/log.txt', 1, debug=True)

if not args.public:
    hash2user['123'] = hash2user[hash_func(users[-1])]

with open('user_information.txt', 'w') as f:
    for key, value in hash2user.items():
        f.write('%s: %s\n' % (value, key))

def main():
    my_obj = id2obj[session['id']]
    data = {
        'template_name_or_list': 'main.html',
        'username': session['username'],
        'cnt': cnt[session['username']],
        'real_name': session['real_name'] if 'real_name' in session \
                else 'Unknown'
    }
    if 'msg' in session:
        data['msg'] = session['msg']
        session.pop('msg')
    else:
        data['msg'] = []
    data['status'] = session['status']

    if session['status'] == 0:# {{{
        if request.method == 'POST':
            certcode = request.form['certcode']
            res, name, msg = my_obj.login(certcode)
            if res:
                session['status'] += 1
                session['msg'] = [msg]
                session['real_name'] = name
                return redirect(url_for('index'))
            else:
                data['msg'] += [msg]
        else:   
            res, name, msg = auto_recognition_attemps(my_obj)
            if res:
                session['status'] += 1
                session['msg'] = [msg]
                session['real_name'] = name
                return redirect(url_for('index'))

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
        else:
            dates = [get_date(i) + [''] for i in range(5)]
            dates[3][2] = 'checked'
            data['dates'] = dates
            data['current'] = 'select date'
            data['msg'] += ['[WRN] one session is only allowed to order one ticket in the same time, or there will be a huge mess. (failure)']
    # }}}
    elif session['status'] == 2:# {{{
        if request.method == 'POST':
            route = request.form['route']
            session['route'] = route.split('|')
            session['status'] += 1
            return redirect(url_for('index'))
        else:
            data['current'] = 'select route'
            data['msg'] += ['[LOG] select date: ' + session['date'][-1]]
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
        else:
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
            next_18_time = get_next_18_time()[0] +\
                    ' 18:00:00 (server time)'

            current_time = get_current_time()
            data['s1'] = 'start now ' + current_time
            data['s2'] = 'start at  ' + next_18_time
            data['msg'] = ['[LOG] select date: ' + session['date'][-1],\
                    '[LOG] select route: ' + session['route'][-1]]
    # }}}
    elif session['status'] == 4:# {{{
        wait = int(session['wait'])
        if wait == 1:
            if 'time' not in session:
                res = my_obj.calc_time()
                session['time'] = res
            data['current'] = 'please wait ...'
            cur = time.time()
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
        result, msg = my_obj.buy(session)
        data['msg'] += msg

        data['fresh'] = np.random.uniform(1.0, 2.0)
        if result:
            session['status'] += 1
            redirect(url_for('index'))
        else:
            try:
                ret = data['msg'][-1]
                s = '[ERR] full return '
                if ret[:len(s)] == s:
                    ret = ret[len(s):]
                ret = json.loads(ret.replace('\'', '"'))
                if ret['returnmsg'] in ['业务逻辑判断失败[用户当天该路线预约次数超过限制，禁止预约]']:
                    data['fresh'] = 0xffffffff
            except:
                pass

# }}}
    elif session['status'] == 6:# {{{
        data['current'] = 'succeed'
        
        WRN = False
        if len(my_obj.names) != 3:
            WRN = True
        for name in my_obj.names:
            if name != session['real_name']:
                WRN = True

        if WRN:
            data['msg'] += ['[ERR] {} found in <name>, is either not a triplet or not equal to the {} <realname>'.format(my_obj.names, session['real_name']), '[ERR] you need to re-login!!!!!!!']
        else:
            data['msg'] += ['[SUC] name checked, exactly {}'.format(session['real_name'])]
        data['wechat'] = my_obj.wechat
        data['msg'] += ['[SUC] get QR code successfully!', \
                '[LOG] please scan the QR code with wechat or open this {} in wechat'.format(my_obj.wechat)]
# }}}
    else:# {{{
        data['msg'] = ['[ERR] no such status', '[WRN] system may have large bugs!']
# }}}
    for each in data['msg']:
        log.save(each, session)
    return render_template(**data)

def login(username=None):# {{{
    if request.method == 'POST':
        username = request.form['username']

    if username in hash2user and \
            (hash2user[username] == 'admin' or running):
        username = hash2user[username]

        if cnt[username] == limit and username != 'admin':
            return render_template('login.html', **{'msg': 'Login limit!'})
        cnt[username] += 1

        session['username'] = username
        ip = request.headers['x_real_ip'] \
                if 'x_real_ip' in request.headers \
                else request.remote_addr
        session['id'] = '{} {} {}'.format(\
                username, get_current_time(True), ip)
        session['status'] = 0   #init
        user2id[username].add(session['id'])
        id2obj[session['id']] = Order(username, session['id'])
        if session['username'] == 'admin':
            log.save('[SUC] login', session, True)
        return redirect(url_for('index'))
    else:
        data = {'msg': '[ERR] system is closed!' if not running else (\
                '[ERR] no such code in data base!' if username \
                else '[I N] please enter your code to log in!'),
                'open': 'disabled' if not running else ''}
        return render_template('login.html', **data)
# }}}

@app.route('/logout')# {{{
def logout():
    try:
        _name, _id = session['username'], session['id']
        id2obj.pop(session['id'])
        user2id[_name].remove(_id)
        cnt[session['username']] -= 1
        log.save('[LOG] log out', session)
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
        log.save('[LOG] undo, status --> %d' % session['status'], session)
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
        _id = session['id']
        for identifier in user2id[username]:
            id2obj.pop(identifier)
        user2id[username].clear()
        cnt[username] = 0
        log.save('[LOG] log out all', {'username': username, 'id': _id})
    except:
        pass
    return redirect(url_for('index'))
# }}}

@app.route('/restart')# {{{
def restart():
    try:
        session['status'] = min(session['status'], 1)
        log.save('[LOG] restart', session)
    except:
        pass
    return redirect(url_for('index'))
# }}}

def admin():# {{{
    logs = log.load()
    st = 0
    ed = st + 100
    
    user_information = {}
    for user, value in user2id.items():
        user_information[user] = [len(value), value]


    data = {
        'template_name_or_list': 'admin.html',
        'username': session['username'],
        'last_operate': last_operate,
        'cnt': cnt[session['username']],
        'user_online': len(id2obj),
        'logs': logs,
        'st': st,
        'ed': ed,
        'current_time': get_current_time(),
        'users': user_information,

    }
    return render_template(**data)
    # }}}

ip_time = 600
ip_limit = 3000

@app.route('/', methods=['GET', 'POST'])# {{{
def index():
    ip = request.remote_addr
    if ip not in ip_count:
        ip_count[ip] = []
    cur = time.time()
    n = len(ip_count[ip])
    i = 0
    while (i < n):
        if ip_count[ip][i] + ip_time > cur:
            break
        i += 1
    ip_count[ip] = ip_count[ip][i:]
    ip_count[ip].append(cur)
    if len(ip_count[ip]) > ip_limit:
        msg = '[ERR] ip blocked! do not access me with high frequency! wait for %.2f minute(s)!' % (ip_time / 60)
        log.save(msg)
        return msg

    if 'username' in session:
        try:
            my_obj = id2obj[session['id']]
        except:
            session.clear()
            return login()
        if session['username'] == 'admin':
            return admin()
        last_operate = get_current_time()
        return main()
    last_operate = get_current_time()
    return login()
# }}}

@app.route('/login/<string:username>')# {{{
def _login(username=None):
    logout()
    return login(username)
# }}}

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/admin')
@app.route('/admin/<string:order>')
def reboot(order=''):
    if 'username' in session and 'id' in session and \
            session['id'] in id2obj and session['username'] == 'admin':
        if order == 'reboot':   
            shutdown_server()
            msg = '[LOG] server reboots...'
            log.save(msg, session)
        elif order == 'shutdown':
            shutdown_server()
            msg = '[LOG] server shuts down...'
            log.save(msg, session)
            os.system('rm running.status')
        elif order == 'start':
            shutdown_server()
            msg = '[LOG] server starts...'
            log.save(msg, session)
            os.system('touch running.status')
        return msg
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    host = '0.0.0.0' if args.public else '127.0.0.1'
    app.secret_key = os.urandom(32)
    log.save('[LOG] system starts!', ignore=True)
    app.run(host=host, port=args.port, debug=True if not args.public else False)
