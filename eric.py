from commom import cfg as ucasbus_cfg
from crawl2.spider import *
from crawl2.utils import *
import os, time, json
import numpy as np
from tools import *
import threading
from certcode.init import *

name_re = re.compile(
        '<li>你好，<a class="c4"  href="#">(.*?)</a></li>', re.S)

urlcode_re = re.compile('toUtf8(.*?);')

def keep_alive(eric):
    while True:
        time.sleep(np.random.randint(300, 500)/100)
        ret = eric.check()
        if not ret:
            res, msg, data = auto_recognition_attemps(eric, attemps=5)
            if res == 0 and data[0] == eric.realname:
                pass
            else:
                eric._login = False

class Eric(object):
    def __init__(self, username):
        self.username = username
        self.page_limit = ucasbus_cfg.page_limit
        self._login = False
        self.cache = Cache(ucasbus_cfg.cache_path)
        self.route_list_cache = Cache(ucasbus_cfg.route_list_path)
        self.user_cache = Cache(\
                os.path.join(ucasbus_cfg.users_path, username))
        self.spider = Spider(encoding='utf-8')
        self.load()

        self.keep_alive = threading.Thread(target=keep_alive, args=(self, ))
        if self.username[:2] == 'ch':
            self.keep_alive.start()

    def check(self):
        response = self.spider.get('http://payment.ucas.ac.cn/NetWorkUI/showPublic')
        if response:
            return self.realname in response.text
        return False

    def load(self):
        self.page = self.user_cache.load('page')
        if not isinstance(self.page, list):
            self.page = []
        self.lock = self.user_cache.load('lock')
        if self.lock == None or not isinstance(self.lock, bool):
            self.lock = False
        self.realname = self.user_cache.load('realname')
        if not self.realname:
            self.realname = 'Unknown'
        
    def save(self):
        self.user_cache.save(self.page, 'page')
        self.user_cache.save(self.lock, 'lock')
        self.user_cache.save(self.realname, 'realname')

    def del_page(self, page):
        if page >= 0 and page < len(self.page):
            self.page[page]['active'] = False
        return self.touch_page()

    def new_page(self):
        n = len(self.page)
        for i in range(n):
            if not self.page[i]['active']:
                self.page[i] = {'status': 1, 'active': True}
                return i
        if n >= self.page_limit:
            return -1
        self.page.append({'status': 1, 'active': True})
        return n

    def touch_page(self, page=-1):
        if page >= 0 and page < len(self.page) and \
                self.page[page]['active']:
            return page
        for i in range(len(self.page)):
            if self.page[i]['active']:
                return i
        return self.new_page()

    def get_certcode(self, prefix=False):# {{{
        url = 'http://payment.ucas.ac.cn/NetWorkUI/authImage'
        name = hash_func('{}{}'.format(self.username, time.time()))+'.jpg'
        certcode_path = os.path.join(ucasbus_cfg.static_folder, name)
        response = self.spider.get(url)
        if not response:
            return ''
        with open(certcode_path, 'wb') as f:
            f.write(response.content)
        return certcode_path if prefix else name
    # }}}
    def login(self, certcode):# {{{
        msg = []
        url = 'http://payment.ucas.ac.cn/NetWorkUI/fontuserLogin'
        data = self.user_cache.load('login')
        data['checkCode'] = certcode
        response = self.spider.post(url, data=data)

        if not response:
            msg += ['[ERR] failed at login: server does not response in time']
            return 1, msg, None

        name = name_re.findall(response.text)
        if len(name) == 0:
            msg += ['[ERR] getting name failed (probably logining failed, wrong certcode)!']
            return 9, msg, None
        else:
            name = name[0]
            msg += ['[SUC] %s logining successfully!' % name]
            return 0, msg, [name]
    # }}}
    def get_route(self, date, cache):# {{{
        url = 'http://payment.ucas.ac.cn/NetWorkUI/queryBusByDate'
        route_list = self.route_list_cache.load(date)
        msg = []
        if not route_list or not cache:
            data = {
                'bookingdate': date,
                'factorycode': 'R001',
            }
            response = self.spider.post(url, data=data)
            if not response:
                msg += ['[ERR] failed at get route: server does not response in time']
                return 1, msg, None
            try:
                data = response.json()
            except:
                msg += ['[ERR] failed at get route: <json> response is not json']
                return 3, msg, None
            try:    
                route_list = data['routelist']
            except:
                msg += ['[ERR] failed at get route: routelist is not a key']
                msg += ['[ERR] json = {}'.format(data)]
                return 4, msg, None

            self.route_list_cache.save(route_list, date)
        return 0, msg, [route_list]
    # }}}
    def calc_time(self, *, delta=ucasbus_cfg.delta, timezone=8):# {{{
        cur = time.time()
        t = 18 * 3600 + delta - (cur + timezone * 3600) % 86400
        if t < 0:
            t += 86400
        return int(t + cur)
    # }}}
    def check_realname(self, step, response):# {{{
        msg = []
        data = name_re.findall(response.text)
        if len(data) == 1 and data[0] == self.realname:
            return 0, msg
        else:
            names = json.dumps(data)
            msg += ['[ERR] failed at #{}: \'{}\' found in <name> is not equal to {}'.format(step, names, self.realname)]
            return step * 10 + 2, msg
    # }}}
    def send_order(self, route, date):# {{{
        msg = []
        data = {
            'routecode': route,  #   You need change
            'payAmt': '6.00',
            'bookingdate': date,    #   You need change
            'payProjectId': '4',        
            'tel': self.user_cache.load('tel'),
            'factorycode': 'R001',
        }
        url = 'http://payment.ucas.ac.cn/NetWorkUI/reservedBusCreateOrder'
        response = self.spider.post(url, data)

        if not response:
            msg += ['[ERR] failed at #1: <send order> server does not response in time']
            return 11, msg, None
        try:
            information = response.json()
        except:
            msg += ['[ERR] failed at #1: <json> response is not json']
            return 13, msg, None

        try:
            ret = information['returncode']
            orderno = information['payOrderTrade']['orderno']
            msg += ['[SUC] #1: orderno={}, order={}'\
                    .format(orderno, data)]
            return 0, msg, [orderno]
        except:
            msg += ['[ERR] returncode or payOrderTrade->orderno not found in json!']
            msg += ['[ERR] #1: return json = {}'.format(information)]
            return 14, msg, None

        msg += ['[ERR] #1: return json = {}'.format(information)]
        return 19, msg, None
    # }}}
    def send_orderno(self, orderno):# {{{
        msg = []
        data = {
            'orderno': orderno,
            'orderamt': '6.00',
            'payType': '03',
            'mess': '',
            'start_limittxtime': '',
            'end_limittxtime': '',
        }
        url = 'http://payment.ucas.ac.cn/NetWorkUI/onlinePay'
        response = self.spider.post(url, data=data)

        if not response:
            msg += ['[ERR] failed at #2: <send orderno> server does not response in time']
            return 21, msg, None
        
        ret, log = self.check_realname(2, response)
        msg += log
        if ret != 0:
            return ret, msg, None
        msg += ['[SUC] orderno({}) posted!'.format(orderno)]
        return 0, msg, None
    # }}}
    def request_wechat_urlcode(self, orderno):# {{{
        msg = []
        url = 'http://payment.ucas.ac.cn/NetWorkUI/weixinPayAction?orderno=%s'%orderno
        response = self.spider.get(url)

        if not response:
            msg += ['[ERR] failed at #3: <request wechat urlcode> server does not response in time']
            return 31, msg, None

        ret, log = self.check_realname(3, response)
        msg += log
        if ret != 0:
            return ret, msg, None

        try:
            urlcode = urlcode_re.findall(response.text)[0][2:-2]
        except:
            msg += ['[ERR] failed at #3: <request wechat urlcode> urlcode is missing in response']
            return 35, msg, None
        msg += ['[SUC] urlcode({}) got from orderno({})'\
                .format(urlcode, orderno)]
        return 0, msg, [urlcode]
    # }}}
    def get_ucas_qrcode(self, urlcode):# {{{
        msg = []
        data = {
            'msgCode': 'SUCCESS',
            'weixinMessage': '??',
            'urlCode': urlcode,
            'key': 'TkVUV09SS1BBWWtleQ==',
        }
        url = 'http://payment.ucas.ac.cn/NetWorkUI/weiXinQRCode?'
        for key, value in data.items():
            url = url + key + '=' + value + '&'
        response = self.spider.get(url)

        if not response:
            msg += ['[ERR] failed at #4: <get ucas qrcode> server does not response in time']
            return 41, msg, None

        ret, log = self.check_realname(4, response)
        msg += log
        if ret != 0:
            return ret, msg, None

        text = response.text.replace('src="/NetWork', 'src="http://payment.ucas.ac.cn/NetWork')
        msg += ['[SUC] html got from urlcode({})'.format(urlcode)]
        return 0, msg, [text]
    # }}}
    def buy(self, route, date):# {{{
        msg = ['[LOG] start ordering']
        '''
            send order
        '''
        ret, log, data = self.send_order(route, date)
        msg += log
        if ret != 0:
            return ret, msg, None
        orderno = data[0]


        ret, log, data = self.send_orderno(orderno)
        msg += log
        if ret != 0:
            return ret, msg, None

            
        ret, log, data = self.request_wechat_urlcode(orderno)
        msg += log
        if ret != 0:
            return ret, msg, None
        urlcode = data[0]

        ret, log, data = self.get_ucas_qrcode(urlcode)
        msg += log
        if ret != 0:
            return ret, msg, None
        html = data[0]

        return 0, msg, [urlcode]
    # }}}
