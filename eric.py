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
        time.sleep(np.random.randint(300, 500))
        if eric.finished:
            return
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
        self._login = True
        self.cache = Cache(ucasbus_cfg.cache_path)
        self.route_list_cache = Cache(ucasbus_cfg.route_list_path)
        self.user_cache = Cache(\
                os.path.join(ucasbus_cfg.users_path, username))
        self.spider = Spider(encoding='utf-8')
        self.load()
        self.finished = False
        self.keep_alive = threading.Thread(target=keep_alive, args=(self, ))
        # self.keep_alive.start()

    def finish(self):
        self.save()
        self.finished = True
        # self.keep_alive.join()

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
            msg += ['[ERR] 登录失败，服务器未响应。']
            return 1, msg, None

        name = name_re.findall(response.text)
        if len(name) == 0:
            msg += ['[ERR] 登录失败，信息错误。']
            return 9, msg, None
        else:
            name = name[0]
            msg += ['[SUC] %s 成功登录！' % name]
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
                msg += ['[ERR] 获取路线失败，服务器未响应。']
                return 1, msg, None
            try:
                data = response.json()
            except:
                msg += ['[ERR] 获取路线失败，返回结果无法 json 化。']
                return 3, msg, None
            try:    
                route_list = data['routelist']
            except:
                msg += ['[ERR] 获取路线失败，未找到 routelist 。']
                msg += ['[ERR] json = {}'.format(data)]
                return 4, msg, None

            self.route_list_cache.save(route_list, date)
        return 0, msg, [route_list]
    # }}}
    def calc_time(self, *, \
            delta=ucasbus_cfg.delta, timezone=8, debug=None):# {{{
        cur = time.time()
        if debug:
            return debug + cur
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
            msg += ['[ERR] #{}: \'{}\' 用户不匹配 {}'.format(step, names, self.realname)]
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
            msg += ['[ERR] #1: 服务器未响应。']
            return 11, msg, None
        try:
            information = response.json()
        except:
            msg += ['[ERR] #1: 返回结果无法 json 化。']
            return 13, msg, None

        try:
            ret = information['returncode']
            orderno = information['payOrderTrade']['orderno']
            msg += ['[SUC] #1: 获取订单号[{}]， 订单信息：{}, {}, {}'.format(orderno, data['bookingdate'][0], data['routecode'][0], data['tel'])]
            return 0, msg, [orderno]
        except:
            msg += ['[ERR] #1:  未找到 returncode 或 payOrderTrade->orderno 字段!']
            msg += ['[ERR] #1: json={}'.format(information)]
            return 14, msg, None

        msg += ['[ERR] step #1: json={}'.format(information)]
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
            msg += ['[ERR] #2:  服务器未响应。']
            return 21, msg, None
        
        ret, log = self.check_realname(2, response)
        msg += log
        if ret != 0:
            return ret, msg, None
        # msg += ['[SUC] #2: 成功发送订单: {}！'.format(orderno)]
        return 0, msg, None
    # }}}
    def request_wechat_urlcode(self, orderno):# {{{
        msg = []
        url = 'http://payment.ucas.ac.cn/NetWorkUI/weixinPayAction?orderno=%s'%orderno
        response = self.spider.get(url)

        if not response:
            msg += ['[ERR] #3: 服务器未响应！']
            return 31, msg, None

        ret, log = self.check_realname(3, response)
        msg += log
        if ret != 0:
            return ret, msg, None

        try:
            urlcode = urlcode_re.findall(response.text)[0][2:-2]
        except:
            msg += ['[ERR] #3: urlcode 字段缺失！']
            return 35, msg, None
        msg += ['[SUC] #3: 成功获从订单[{}]中获取urlcode[{}]！'.format(orderno, urlcode)]
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
            msg += ['[ERR] #4: 服务器未响应！']
            return 41, msg, None

        ret, log = self.check_realname(4, response)
        msg += log
        if ret != 0:
            return ret, msg, None

        text = response.text.replace('src="/NetWork', 'src="http://payment.ucas.ac.cn/NetWork')
        msg += ['[SUC] 成功生成二维码，根据urlcode[{}]！'.format(urlcode)]
        return 0, msg, [text]
    # }}}
    def buy(self, route, date):# {{{
        msg = ['[LOG] 开始购票。']
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
