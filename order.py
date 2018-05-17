from commom import sub_cfg
from crawl2.spider import *
from crawl2.utils import *
import os, time
from hash_table import hash_func

def success_judge(response):# {{{
    response.encoding = 'utf-8'
    return '你好' in response.text
# }}}

class Order(object):
    def __init__(self, username, identifier):
        self.logout = False
        self.username = username
        self.id = identifier
        self.cache_path = sub_cfg.cache_path
        self.cache = Cache(self.cache_path)
        self.route_list_cache = Cache(sub_cfg.route_list_path)
        self.user_path = os.path.join(sub_cfg.user_save_file, username)
        self.user_cache = Cache(self.user_path)
        self.spider = Spider()
        self.user_file = os.path.join(sub_cfg.user_save_file, username)
        self.html_path = sub_cfg.html_path
    
    def get_certcode(self):
        url = 'http://payment.ucas.ac.cn/NetWorkUI/authImage'
        name = hash_func('{}{}'.format(self.id, time.time())) + '.jpeg'
        certcode_path = \
                os.path.join('static', name)
        response = self.spider.get(url)
        with open(certcode_path, 'wb') as f:
            f.write(response.content)
        return name

    def login(self, certcode):
        url = 'http://payment.ucas.ac.cn/NetWorkUI/fontuserLogin'
        data = self.user_cache.load('login')
        data['checkCode'] = certcode

        response = self.spider.post(\
                url, data=data, headers=self.spider.headers)
        return success_judge(response)

    def first_step(self, date):# {{{ 
        url = 'http://payment.ucas.ac.cn/NetWorkUI/queryBusByDate'
        data = {
            'bookingdate': date,
            'factorycode': 'R001',
        }
        return self.spider.post(url, data)
    # }}}
    def get_route(self, date, cache):# {{{
        route_list = self.route_list_cache.load(date)
        if not route_list or not cache:
            print('!!!!! no cache')
            response = self.first_step(date)
            route_list = response.json()['routelist']
            self.route_list_cache.save(route_list, date)
        return route_list
    # }}}
    def calc_time(self):
        cur = time.time()
        t = 18 * 3600 + sub_cfg.delta - (cur + 8 * 3600) % 86400
        if t < 0:
            t += 86400
        return int(t + cur)

    def second_step(self):# {{{
        data = {
            'routecode': self.route,  #   You need change
            'payAmt': '6.00',
            'bookingdate': self.date,    #   You need change
            'payProjectId': '4',        
            'tel': self.user_cache.load('tel'),
            'factorycode': 'R001',
        }
        url = 'http://payment.ucas.ac.cn/NetWorkUI/reservedBusCreateOrder'
        response = self.spider.post(url, data)
        return response
    # }}}
    def third_step(self, information):# {{{
        data = {
            'orderno': information['payOrderTrade']['orderno'],
            'orderamt': '6.00',
            'payType': '03',
            'mess': '',
            'start_limittxtime': '',
            'end_limittxtime': '',
        }
        url = 'http://payment.ucas.ac.cn/NetWorkUI/onlinePay'
        response = self.spider.post(url, data=data)
        return response
    # }}}
    def fouth_step(self, information):# {{{
        url='http://payment.ucas.ac.cn/NetWorkUI/weixinPayAction?orderno=%s'\
                %information['payOrderTrade']['orderno']
        response = self.spider.get(url)
        return response
    # }}}
    def fifth_step(self, urlcode):# {{{
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
        response.encoding = 'utf-8'
        text = response.text.replace('src="/NetWork', 'src="http://payment.ucas.ac.cn/NetWork')
        return text
    # }}}
    def buy(self, s):
        log = ['[LOG] start buying']
        self.route, self.date = s['route'], s['date']

        try:
            response = self.second_step()
        except:
            log.append('[ERR] failed in step 2 @ spider')
            return False, log
        try:
            information = response.json()
            ret = information['returncode']
        except:
            log.append('[ERR] failed in step 2 @ json()')
            return False, log

        log.append('[LOG] step2 server return code: ' + ret)
        if ret == 'SUCCESS':
            try:
                self.third_step(information)
            except:
                log.append('[ERR] failed in step 3 @ spider')
                return False, log
            try:
                response = self.fouth_step(information)
            except:
                log.append('[ERR] failed in step 4 @ spider')
                return False, log
            
            try:
                urlcode = re.compile('toUtf8(.*?);').\
                        findall(response.text)[0][2:-2]
            except:
                log.append('[ERR] failed in step 4 @ re')
                return False, log
            self.wechat = urlcode

            try:
                text = self.fifth_step(urlcode)
                self.text = text
                log.append('[SUC] all succeed')
                return True, log
            except:
                log.append('[ERR] failed in step 5 @ spider')
                return False, log

        else:
            log.append('[ERR] full return {}'.format(information))
            return False, log
            

        


