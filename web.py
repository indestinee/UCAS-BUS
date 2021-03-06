from flask import Flask, render_template, session, \
        redirect, url_for, escape, request, Response
import re, argparse, os, pickle, time, json
import numpy as np

from eric import Eric
from tools import *
from log import Log 
from certcode.init import *
from commom import cfg as ucasbus_cfg


def get_web_args():# {{{
    parser = argparse.ArgumentParser(description='bus ticket')
    parser.add_argument('--public', action='store_true', default=False)
    parser.add_argument('--port', default=1234, type=int)
    parser.add_argument('--host', default='127.0.0.1', type=str)
    args = parser.parse_args()
    return args
# }}}

if __name__ == '__main__':# {{{
    print('[LOG] preparing system..')
    args = get_web_args()
    news, error_list = None, []
    if os.path.isfile(ucasbus_cfg.news):
        with open(ucasbus_cfg.news, 'r') as f:
            news = f.read()
    if os.path.isfile(ucasbus_cfg.error_list):
        with open (ucasbus_cfg.error_list, 'r') as f:
            data = f.read().split('\n')
        error_list = [each.split('|') for each in data]

    running = os.path.isfile(ucasbus_cfg.running_status_file)
    
    app = Flask(__name__, static_folder=ucasbus_cfg.static_folder,\
            static_url_path=ucasbus_cfg.static_url_path)

    users = os.listdir(ucasbus_cfg.users_path)
    user2hash = {user: hash_func(user) for user in users}
    hash2user = {user2hash[user]: user for user in users}
    user_counters = {user: 0 for user in users}
    user2id = {user: set() for user in users}
    user2eric = {user: Eric(user) for user in users}

    current_time = get_current_time(True).split(' ')[0]
    log_path = os.path.join(ucasbus_cfg.log_path, current_time)
    log = Log(log_path, 100, debug=True)
    print('[LOG] log file %s' % log_path)
    if not args.public:
        hash2user['123'] = hash2user[hash_func(users[0])]
        print('[LOG] debuging mode, code 123 are open')
    print('[LOG] normal mode')
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
            data['current'] = '【登录 UCAS】'
    else:   
        ret, msg, name = auto_recognition_attemps(eric)
        data['msg'] += msg
        if ret == 0:
            return name[0]
        else:
            path = eric.get_certcode()
            data['certcode_path'] = path
            data['current'] = '【登录 UCAS】'
    return None
# }}}
    
def main(username, identifier, page):# {{{
    ''' init# {{{
    '''
    eric = user2eric[username]
    realname = eric.realname
    n_page = eric.touch_page(page)
    if 'msg' not in session:
        session['msg'] = []
    if n_page != page:
        session['msg'] += ['[ERR] 该页不存在！']
        return redirect('/' + str(n_page))
    
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
    
    data['msg'] = session['msg']
    session['msg'] = []
    # }}}

    if eric._login and not eric.check():
        data['msg'] += ['[WRN] UCAS 远程离线，尝试自动登录！']
        res, logs, names = auto_recognition_attemps(eric)
        data['msg'] += logs
        if res == 0 and names[0] == eric.realname:
            pass
        else:
            eric._login = False
            session['msg'] += data['msg']
            return redirect('/' + str(page))

    if not eric._login:# {{{
        ret = login_ucas(eric, data)
        if ret and (ret == eric.realname or eric.realname == 'Unknown'):
            session['msg'] += data['msg']
            eric._login = True
            eric.realname = ret
            return redirect('/' + str(page))
    # }}}
    elif status == 1:# {{{
        if request.method == 'POST':
            date = request.form['date']
            session['msg'] += data['msg']
            inform['cache'] = True if 'cache' in request.form else False
            inform['query'] = True if 'query' in request.form else False
            inform['date'] = date.split('|')
            inform['status'] += 1
            return redirect('/' + str(page))
        else:
            dates = [get_date_day(i) + [''] for i in range(5)]
            dates[3][2] = 'checked'
            data['dates'] = dates
            data['current'] = '【选择日期】'
    # }}}
    elif status == 2:# {{{
        if request.method == 'POST':
            route = request.form['route']
            inform['route'] = route.split('|')
            inform['status'] += 1
            session['msg'] += data['msg']
            return redirect('/' + str(page))
        else:
            data['current'] = '【选择路线】'
            data['msg'] += ['[LOG]  选择日期: ' + inform['date'][-1]]
            ret, logs, raw = eric.get_route(inform['date'][0], \
                        inform['cache'])
            
            data['msg'] += logs
            if ret == 0:
                raw_route_list = raw[0] 
                route_list = [[route['routecode'], route['routename'],\
                        '', ''] for route in raw_route_list]

                if inform['query']:
                    for each in route_list:
                        query_data = {
                            'routecode': each[0],
                            'bookingdate': inform['date'][0],
                            'factorycode': 'R001',
                        }   
                        remain = eric.query_remain(query_data)
                        each[-1] = remain
                
                def mark_favorite(favorites):
                    for favorite in favorites:
                        for each in route_list:
                            if favorite in each[1] and \
                                    '助教' not in each[1]:
                                each[2] = 'checked'
                                return True
                    return False

                for each in route_list:
                    if '助教' in each[1]:
                        each[2] = 'disabled'

                mark_favorite(\
                        ['玉泉路—雁栖湖18:00', '雁栖湖—玉泉路13:00'])
                data['route_list'] = route_list
            else:
                data['route_list'] = [['0', '[ERR] 路线查询失败，无法从 UCAS 服务器获取路线。', 'disabled']]
                data['msg'] += ['[ERR] %d:  路线查询失败，无法从 UCAS 服务器获取路线。' % ret]
                data['error_list'] = error_list
        
        
    # }}}
    elif status == 3:# {{{
        if request.method == 'POST':
            wait = request.form['time']
            inform['wait'] = wait
            inform['status'] += 1
            inform['msg'] = data['msg']
            return redirect('/' + str(page))
        else:
            data['current'] = '【选择抢票时间】'
            def get_next_18_time():
                cur = (time.time() + 8 * 3600) % 86400 / 3600 
                return get_date_day(1 if cur >= 18 else 0)
            _date = time.localtime(time.time())
            h, m = _date.tm_hour, _date.tm_min

            data['t1'], data['t2'] = '', ''
            if h >= 16 and h < 18:
                data['t2'] = 'checked'
            else:
                data['t1'] = 'checked'
            next_18_time = get_next_18_time()[0] +\
                    ' 18:00:00'

            current_time = get_current_time()
            data['s1'] = '现在预定 ' + current_time
            data['s2'] = '预约抢票 ' + next_18_time
            data['msg'] += ['[LOG] 选择日期: ' + inform['date'][-1],\
                    '[LOG] 选择路线: ' + inform['route'][-1]]
            inform['ttime'] = None
    # }}}
    elif status == 4:# {{{
        wait = int(inform['wait'])
        if wait == 1:
            cur = time.time() 
            data['current'] = '【等待抢票】'
            if inform['ttime']:
                res = inform['ttime']
            else:
                res = eric.calc_time()
                inform['ttime'] = res

            if cur > res:
                inform['status'] += 1
                inform['attemps'] = 0
                session['msg'] = data['msg']
                return redirect('/' + str(page))
            data['msg'] += ['[LOG] 选择日期: ' + inform['date'][-1],\
                    '[LOG] 选择路线: ' + inform['route'][-1]]

            delta = int(res - cur)
            data['fresh'] = min(max(1, delta//3),\
                    np.random.randint(300, 500))
            eta = ''
            if delta > 3600:
                eta += '%d小时'%(delta//3600)
                delta %= 3600
            if delta > 60:
                eta += '%d分'%(delta//60)
                delta %= 60
            eta += '%d秒'%delta
            data['cur_time'] = get_current_time()
            data['eta'] = eta
        else:
            inform['status'] += 1
            inform['attemps'] = 0
            session['msg'] += data['msg']
            return redirect('/' + str(page))
# }}}
    elif status == 5:# {{{
        inform['attemps'] += 1
        data['current'] = '【正在抢票】第 %d 次...' % \
                inform['attemps']
        result, msg, raw = eric.buy(inform['route'], inform['date'])
        data['msg'] += msg
        data['fresh'] = np.random.uniform(1.0, 2.0)
        if result == 0:
            inform['status'] += 1
            inform['urlcode'] = raw[0]
            session['msg'] += data['msg']
            return redirect('/' + str(page))
        else:
            ret = data['msg'][-1]
            data['msg'] += ['[ERR] code %d' % result]
            data['error_list'] = error_list
            try:
                l = ret.find('{')
                r = ret[::-1].find('}')
                r = None if r == 0 else -r
                if l != -1 and r != -1:
                    ret = ret[l:r]
                ret = json.loads(ret.replace('\'', '"'))
                if ret['returnmsg'] in ['业务逻辑判断失败[用户当天该路线预约次数超过限制，禁止预约]']:
                    data['fresh'] = None
                else:
                    pass

            except:
                pass

# }}}
    elif status == 6:# {{{
        data['current'] = '【成功预约】'
        data['wechat'] = inform['urlcode']
        if len(data['msg']) == 0 and 'suc_history' in inform:
            data['msg'] = inform['suc_history']
        else:
            data['msg'] += [
                '[SUC] 请扫码支付！'
            ]
            inform['suc_history'] = data['msg']

# }}}
    else:# {{{
        data['msg'] = ['[ERR] 非法状态！请报告管理员！']
# }}}
    for each in data['msg']:
        log.save(each, session)
    return render_template(**data)
# }}}
def login(_username=None):# {{{
    if request.method == 'POST':
        _username = request.form['username']
    
    username = hash2user[_username] if _username in hash2user else None
    
    if username and (username == 'admin' or running):
        session['username'] = username

        eric = user2eric[username]
        if eric.lock:
            return render_template('login.html', \
                    **{'msg': '[ERR] 该用户处于锁定状态！'\
                    , 'news': news})

        if user_counters[username] == ucasbus_cfg.online_limit \
                and username != 'admin':
            return render_template('login.html', \
                    **{'msg': '[ERR] 过多终端在线，限制登录！',\
                    'news': news})

        user_counters[username] += 1

        ip = request.headers['x_real_ip'] \
                if 'x_real_ip' in request.headers else request.remote_addr

        session['id'] = '{} {} {}'.format(\
                username, get_current_time(True), ip)

        user2id[username].add(session['id'])
        session['realname'] = eric.realname
        page = eric.touch_page()
        return redirect('/' + str(page))
    else:
        data = {'msg': '[ERR] 系统关闭！' if not running else (\
                '[ERR] 该用户不存在！' if _username \
                else '[I N] 请输入密钥登录'),
                'open': 'disabled' if not running else '', 'news': news}
        return render_template('login.html', **data)
# }}}


def alive():# {{{
    username = session['username'] if 'username' in session else None
    identifier = session['id'] if 'id' in session else None
    if username and identifier and identifier in user2id[username]:
        return True, username, identifier
    return False, None, None
# }}}
@app.route('/logout')
def logout():# {{{
    ret, username, identifier = alive()
    if ret:
        user2id[username].remove(identifier)
        user_counters[username] -= 1
        log.save('[LOG] log out', session)
    session.clear()
    return redirect(url_for('index'))
# }}}
@app.route('/logout_all')
def logout_all(username=None, inside=False):# {{{
    if not inside:
        ret, username, identifier = alive()
    else:
        ret = True

    if ret:
        user2id[username].clear()
        user_counters[username] = 0
        log.save('[LOG] log out all', session)

    if not inside:
        session.clear()
        return redirect(url_for('index'))
# }}}
@app.route('/undo')
@app.route('/undo/<int:page>')
def undo(page=-1):# {{{
    ret, username, identifier = alive()
    if ret:
        eric = user2eric[username]
        npage = eric.touch_page(page)
        if npage != page:
            session['msg'] = ['[ERR] no such page id']
            return redirect('/' + str(npage))
        
        inform = eric.page[page]
        if inform['status'] >= 5:
            inform['status'] = 3
        elif inform['status'] > 1:
            inform['status'] -= 1
        return redirect('/' + str(npage))
    else:
        session.clear()
        return redirect(url_for('index'))
# }}}
@app.route('/restart')
@app.route('/restart/<int:page>')
def restart(page=-1):# {{{
    ret, username, identifier = alive()
    if ret:
        eric = user2eric[username]
        npage = eric.touch_page(page)
        if npage != page:
            session['msg'] = ['[ERR]  该页不存在！']
            return redirect('/' + str(npage))

        username = session['username']
        eric = user2eric[username]
        inform = eric.page[page]
        inform['status'] = min(inform['status'], 1)
        return redirect('/' + str(npage))
    else:
        session.clear()
        return redirect(url_for('index'))
# }}}
@app.route('/new_page')
@app.route('/new_page/<int:page>')
def new_page(page=0):# {{{
    ret, username, identifier = alive()
    if ret:
        eric = user2eric[username]
        npage = eric.new_page()
        if npage == -1:
            npage = page
            session['msg'] = ['[ERR] 页数过多，无法创建！']
        return redirect('/' + str(npage))
    session.clear()
    return redirect(url_for('index'))
# }}}
@app.route('/del_page')
@app.route('/del_page/<int:page>')
def del_page(page=-1):# {{{
    ret, username, identifier = alive()
    if ret:
        eric = user2eric[username]
        page = eric.del_page(page)
        return redirect('/' + str(page))
    session.clear()
    return redirect(url_for('index'))
# }}}
@app.route('/del_all_page')
def del_all_page(username=None, inside=False):# {{{
    if not inside:
        ret, username, identifier = alive()
    else:
        ret = True
    if ret:
        eric = user2eric[username]
        eric.page.clear()
        if not inside:
            page = eric.touch_page()
            return redirect('/' + str(page))
    if not inside:
        return redirect(url_for('index'))
# }}}
@app.route('/del_other_page/<int:page>')
def del_other_page(page):# {{{
    ret, username, identifier = alive()
    if ret:
        eric = user2eric[username]
        for i in range(len(eric.page)):
            eric.del_page(i)
        page = eric.touch_page()
        return redirect('/' + str(page))
    return redirect(url_for('index'))
# }}}

@app.route('/', methods=['GET', 'POST'])
@app.route('/<int:page>', methods=['GET', 'POST'])
def index(page=0):# {{{
    ret, username, identifier = alive()
    if ret:
        if username == 'admin':
            return redirect('/admin')
        else:
            return main(username, identifier, page)
    else:
        session.clear()
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

''' admin '''
@app.route('/admin')
@app.route('/admin/<string:order>')
@app.route('/admin/<string:order>/<string:user>')
def admin(order='', user=''):# {{{
    order_list = set(['', 'system', 'login', 'logout', 'delpage', 'lock', 'unlock', 'log', 'code'])

    if order not in order_list:
        return redirect('/admin')

    ret, username, identifier = alive()
    if not ret:
        session.clear()
        return redirect(url_for('index'))

    
    user_list = [u for u in user2id.keys() if u != 'admin']
    user_list.sort()


    data = {
        'template_name_or_list': 'admin.html',
        'username': username,
        'online': user_counters[username],
        'user_list': user_list,
        'order': order,
        'back': True if order not in ['', 'log', 'code'] else False
    }

    
    if order == '':
        user_status = {u: {'realname': user2eric[u].realname, \
                'lock': user2eric[u].lock, \
                'pages': len(user2eric[u].page), \
                'online': user_counters[u]} for u in user_list}
        data['inform'] = user_status

    elif order == 'system':
        return reboot(user)
    elif order == 'login':
        if user not in user2id:
            return redirect('/admin')
        user2id[username].remove(identifier)
        user_counters[username] -= 1
        session.clear()
        return login(user2hash[user])
    elif order == 'logout':
        if user not in user2id:
            return redirect('/admin')
        logout_all(user, True)
    elif order == 'delpage':
        if user not in user2id:
            return redirect('/admin')
        del_all_page(user, True)
    elif order == 'lock':
        if user not in user2id:
            return redirect('/admin')
        user2eric[user].lock = True
    elif order == 'unlock':
        if user not in user2id:
            return redirect('/admin')
        user2eric[user].lock = False
    elif order == 'log':
        try:
            st = max(int(user), 0)
        except:
            st = 0
        logs = log.load(st, user)
        data['logs'] = logs
        data['nxt'] = st + ucasbus_cfg.logsize
        data['pre'] = max(0, st - ucasbus_cfg.logsize)
    elif order == 'code':
        if user not in user2id:
            return redirect('/admin')
        data['code'] = user2hash[user]
        data['user'] = 'All'
    return render_template(**data)
    # }}}

def reboot(order):# {{{
    ret, username, identifier = alive()
    if ret:
        for key, eric in user2eric.items():
            eric.finish()
        log.finish()
        shutdown_server()
        if order == 'reboot':   
            msg = '[LOG] server rebooting...'
            log.save(msg, session)
        elif order == 'shutdown':
            msg = '[LOG] server shutting down...'
            log.save(msg, session)
            os.system('rm %s' % ucasbus_cfg.running_status_file)
        elif order == 'start':
            msg = '[LOG] server starting...'
            log.save(msg, session)
            os.system('touch %s'%ucasbus_cfg.running_status_file)
        else:
            return redirect('/admin')
        return render_template('error.html')
    else:
        session.clear()
        return redirect(url_for('index'))
# }}}

if __name__ == '__main__':# {{{
    app.secret_key = os.urandom(32)
    log.save('[LOG] system starts!', ignore=True)
    print('[LOG] opening system!')
    app.run(host=args.host, port=args.port, debug=True if not args.public else False)
# }}}
