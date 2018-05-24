from flask import Flask, render_template, session, \
        redirect, url_for, escape, request, Response
import re, argparse, os, pickle, time, json
import numpy as np

from eric import Eric
from tools import *
from certcode.raw_data import recognition
from log import Log 
from certcode.init import *
from commom import cfg as ucasbus_cfg


def get_web_args():# {{{
    parser = argparse.ArgumentParser(description='bus ticket')
    parser.add_argument('--public', action='store_true', default=False)
    parser.add_argument('--port', default=1234, type=int)
    args = parser.parse_args()
    return args
# }}}
if __name__ == '__main__':# {{{
    args = get_web_args()
    running = os.path.isfile(ucasbus_cfg.running_status_file)
    ip_counters = {}
    app = Flask(__name__, static_folder=ucasbus_cfg.static_folder,\
            static_url_path=ucasbus_cfg.static_url_path)

    users = os.listdir(ucasbus_cfg.users_path)
    hash2user = {hash_func(user): user for user in users}
    user_counters = {user: 0 for user in users}
    user2id = {user: set() for user in users}
    user2eric = {}
    current_time = get_current_time(True)
    log = Log(os.path.join(ucasbus_cfg.log_path, current_time), \
            1, debug=True)

    if not args.public:
        hash2user['123'] = hash2user[hash_func(users[0])]

    with open('user_information.txt', 'w') as f:
        for key, value in hash2user.items():
            f.write('%s: %s\n' % (value, key))
# }}}
def login_ucas(eric, data): # {{{
    if request.method == 'POST':
        certcode = request.form['certcode']
        ret, msg, name = eric.login(certcode)
        data['msg'] += msg
        if ret == 0:
            return name[0]
        else:
            path = eric.get_certcode()
            data['certcode_path'] = path
            data['current'] = 'enter certcode and login in payment'
    else:   
        ret, msg, name = auto_recognition_attemps(eric, attemps=5)
        data['msg'] += msg
        if ret == 0:
            return name[0]
        else:
            path = eric.get_certcode()
            data['certcode_path'] = path
            data['current'] = 'enter certcode and login in payment'
    return None
# }}}
    
def main():
    ''' init# {{{
    '''
    username, identifier =\
            session['username'], session['id']
    
    eric = user2eric[username]
    realname = eric.realname
    page = session['page']
    if page >= len(eric.page):
        page = eric.new_page()
        session['page'] = page
    
    inform = eric.page[page]
    status = inform['status']

    data = {
        'template_name_or_list': 'main.html',
        'username': username,
        'realname': realname,
        'cnt': user_counters[username],
        'status': status,
        'login': eric._login,
        'total_page': len(eric.page),
        'pages': eric.page,
        'page': page,
    }
    
    if 'msg' in session:
        data['msg'] = session['msg']
        session.pop('msg')
    else:
        data['msg'] = []
    # }}}

    if not eric._login:# {{{
        ret = login_ucas(eric, data)
        if ret != None:
            session['msg'] = data['msg']
            eric._login = True
            eric.realname = ret
            return redirect(url_for('index'))
    # }}}
    elif status == 1:# {{{
        if request.method == 'POST':
            date = request.form['date']
            session['msg'] = data['msg']
            inform['cache'] = True if 'cache' in request.form else False
            inform['date'] = date.split('|')
            inform['status'] += 1
            return redirect(url_for('index'))
        else:
            dates = [get_date_day(i) + [''] for i in range(5)]
            dates[3][2] = 'checked'
            data['dates'] = dates
            data['current'] = 'select date'
    # }}}
    elif status == 2:# {{{
        if request.method == 'POST':
            route = request.form['route']
            inform['route'] = route.split('|')
            inform['status'] += 1
            session['msg'] = data['msg']
            return redirect(url_for('index'))
        else:
            data['current'] = 'select route'
            data['msg'] += ['[LOG] select date: ' + inform['date'][-1]]
            ret, logs, raw = eric.get_route(inform['date'][0], \
                        inform['cache'])
            data['msg'] += logs
            if ret == 0:
                raw_route_list = raw[0] 
                route_list = [[route['routecode'], \
                        'name: {}, time: {}, code: {}'\
                    .format(route['routename'], route['routetime'],\
                    route['routecode']), ''] for route in raw_route_list]

                def mark_favorite(favorites):
                    for favorite in favorites:
                        for each in route_list:
                            if favorite in each[1] and \
                                    '助教' not in each[1]:
                                each[2] = 'checked'
                                return True

                for each in route_list:
                    if '助教' in each[1]:
                        each[2] = 'disabled'

                mark_favorite(\
                        ['玉泉路—雁栖湖18:00', '雁栖湖—玉泉路13:00'])
                data['route_list'] = route_list
            else:
                data['route_list'] = [['0', '[ERR] request route list error! payment@ucas may not open', 'disabled']]
        
    # }}}
    elif status == 3:# {{{
        if request.method == 'POST':
            wait = request.form['time']
            inform['wait'] = wait
            inform['status'] += 1
            inform['msg'] = data['msg']
            return redirect(url_for('index'))
        else:
            data['current'] = 'choose order time'
            def get_next_18_time():
                cur = (time.time() + 8 * 3600) % 86400 / 3600 
                return get_date_day(1 if cur >= 18 else 0)
            _date = time.localtime(time.time())
            h, m = _date.tm_hour, _date.tm_min

            data['t1'], data['t2'] = '', ''
            if h >= 18 and h <= 18:
                data['t1'] = 'checked'
            else:
                data['t2'] = 'checked'
            next_18_time = get_next_18_time()[0] +\
                    ' 18:00:00'

            current_time = get_current_time()
            data['s1'] = 'start at ' + current_time + ' current time'
            data['s2'] = 'start at ' + next_18_time + ' server time'
            data['msg'] = ['[LOG] select date: ' + inform['date'][-1],\
                    '[LOG] select route: ' + inform['route'][-1]]
    # }}}
    elif status == 4:# {{{
        wait = int(inform['wait'])
        if wait == 1:
            if 'time' not in inform:
                res = eric.calc_time()
                inform['time'] = res
            data['current'] = 'please wait ...'
            cur = time.time()
            if cur > inform['time']:
                inform['status'] += 1
                inform['attemps'] = 0
                session['msg'] = data['msg']
                return redirect(url_for('index'))
            delta = int(inform['time'] - cur)
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
            inform['status'] += 1
            inform['attemps'] = 0
            session['msg'] = data['msg']
            return redirect(url_for('index'))
# }}}
    elif status == 5:# {{{
        inform['attemps'] += 1
        data['current'] = 'sending order information [%d]...' % \
                inform['attemps']
        result, msg, raw = eric.buy(inform['route'], inform['date'])
        data['msg'] += msg
        data['fresh'] = np.random.uniform(1.0, 2.0) * 10000
        if result == 0:
            inform['status'] += 1
            inform['urlcode'] = raw[0]
            session['msg'] = data['msg']
            return redirect(url_for('index'))
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
    elif status == 6:# {{{
        data['current'] = 'succeed'
        
        data['wechat'] = inform['urlcode']
        data['msg'] += ['[SUC] get QR code successfully!', \
                '[LOG] please scan the QR code with wechat or open this {} in wechat'.format(inform['urlcode'])]
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
    
    username = hash2user[username] if username in hash2user else None
    
    if username and (username == 'admin' or running):
        session['username'] = username

        if user_counters[username] == ucasbus_cfg.online_limit \
                and username != 'admin':
            return render_template('login.html', \
                    **{'msg': '[ERR] login limit, too many accounts online. contact to admin.'})
        user_counters[username] += 1

        ip = request.headers['x_real_ip'] \
                if 'x_real_ip' in request.headers else request.remote_addr

        session['id'] = '{} {} {}'.format(\
                username, get_current_time(True), ip)

        user2id[username].add(session['id'])
        if username not in user2eric:
            user2eric[username] = Eric(username, ucasbus_cfg.page_limit)
        eric = user2eric[username]
        session['realname'] = eric.realname
        session['page'] = eric.first_page()
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
        user2id[_name].remove(_id)
        user_counters[_name] -= 1
        log.save('[LOG] log out', session)
        session.clear()
    except:
        pass
    return redirect(url_for('index'))
# }}}

@app.route('/undo')
def undo():# {{{
    try:
        username = session['username']
        eric = user2eric[username]
        inform = eric.page[session['page']]
        if inform['status'] >= 5:
            inform['status'] = 3
        elif inform['status'] > 1:
            inform['status'] -= 1
    except:
        pass
    return redirect(url_for('index'))
# }}}
@app.route('/refresh')
def refresh():# {{{
    return redirect(url_for('index'))
# }}}
@app.route('/logout_all')
def logout_all():# {{{
    try:
        username = session['username']
        user2id[username].clear()
        user_counters[username] = 0
        log.save('[LOG] log out all', session)
        session.clear()
    except:
        pass
    return redirect(url_for('index'))
# }}}
@app.route('/restart')
def restart():# {{{
    try:
        username = session['username']
        eric = user2eric[username]
        inform = eric.page[session['page']]
        inform['status'] = min(inform['status'], 1)
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
        'cnt': user_counters[session['username']],
        'user_online': len(user2id),
        'logs': logs,
        'st': st,
        'ed': ed,
        'current_time': get_current_time(),
        'users': user_information,

    }
    return render_template(**data)
    # }}}


@app.route('/', methods=['GET', 'POST'])
def index():# {{{
    if 'username' in session:
        if session['username'] == 'admin':
            return admin()
        if session['id'] not in user2id[session['username']]:
            session.clear()
            return login()
        return main()
    else:
        return login()
# }}}

@app.route('/login')
@app.route('/login/<string:username>')
def _login(username=None):# {{{
    logout()
    return login(username)
# }}}

def shutdown_server():# {{{
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
# }}}

@app.route('/page')
@app.route('/page/<int:page>')
def change_page(page=0):# {{{
    session['page'] = page
    return redirect(url_for('index'))
# }}}
@app.route('/del_page')
@app.route('/del_page/<int:page>')
def del_page(page=-1):# {{{
    if page >= 0:
        try:
            username = session['username']
            eric = user2eric[username]
            eric.del_page(page)
            if page == session['page']:
                session['page'] = eric.first_page()
        except:
            pass
    return redirect(url_for('index'))
# }}}
@app.route('/admin')
@app.route('/admin/<string:order>')
def reboot(order=''):# {{{
    if 'username' in session and 'id' in session and \
            session['id'] in id2eric and session['username'] == 'admin':
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
            os.system('touch %s'%ucasbus_cfg.running_status_file)
        return msg
    else:
        return redirect(url_for('index'))
# }}}
if __name__ == '__main__':# {{{
    host = '0.0.0.0' if args.public else '127.0.0.1'
    app.secret_key = os.urandom(32)
    log.save('[LOG] system starts!', ignore=True)
    app.run(host=host, port=args.port, debug=True if not args.public else False)
# }}}
