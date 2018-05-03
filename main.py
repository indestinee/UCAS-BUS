from crawl2.spider import *
from crawl2.utils import *
import time, os
import argparse

delta = 90 - 8 # delta of local time and server time

user_save_file = 'data'

def get_args():
    parser = argparse.ArgumentParser(description='UCAS_BUS')
    parser.add_argument('-u', '--user', default='default')
    parser.add_argument('-a', '--anonymous', action='store_true', default=False)
    args = parser.parse_args()
    return args

args = get_args()

cache = Cache('./cache')

html_path = 'html_cache'
touchdir(html_path)

spider = Spider()

def success_judge(response):# {{{
    response.encoding = 'utf-8'
    return '你好' in response.text
# }}}
def first_step():# {{{ 
    url = 'http://payment.ucas.ac.cn/NetWorkUI/queryBusByDate'
    print('[LOG] posting to', url)
    data = {
        'bookingdate': cache.date,
        'factorycode': 'R001',
    }
    response = spider.post(url, data)
    spider.html_save(response, 'first_step.html')
    return response
# }}}
def second_step():# {{{
    data = {
        'routecode': cache.route['routecode'],  #   You need change
        'payAmt': '6.00',
        'bookingdate': cache.date,    #   You need change
        'payProjectId': '4',        
        'tel': user_cache.load('tel'),
        'factorycode': 'R001',
    }
    print('[LOG] order information:', data)
    url = 'http://payment.ucas.ac.cn/NetWorkUI/reservedBusCreateOrder'
    print('[LOG] step 2, posting to', url)
    response = spider.post(url, data)
    spider.html_save(response, 'second_step.html')
    return response
# }}}
def third_step(information):# {{{
    data = {
        'orderno': information['payOrderTrade']['orderno'],
        'orderamt': '6.00',
        'payType': '03',
        'mess': '',
        'start_limittxtime': '',
        'end_limittxtime': '',
    }
    url = 'http://payment.ucas.ac.cn/NetWorkUI/onlinePay'
    print('[LOG] step 3, posting to', url)
    response = spider.post(url, data=data)
    spider.html_save(response, 'third_step.html')
    return response
# }}}
def fouth_step(information):# {{{
    url='http://payment.ucas.ac.cn/NetWorkUI/weixinPayAction?orderno=%s'\
            %information['payOrderTrade']['orderno']
    if not args.anonymous:
        print('[LOG] step 4, getting from', url)
    response = spider.get(url)
    spider.html_save(response, 'fouth_step.html')
    print('[OPT] please open the website shown above to pay the ticket! remembet to login before open.')
    return response
# }}}
def fifth_step(urlcode):# {{{
    data = {
        'msgCode': 'SUCCESS',
        'weixinMessage': '??',
        'urlCode': urlcode,
        'key': 'TkVUV09SS1BBWWtleQ==',
    }
    url = 'http://payment.ucas.ac.cn/NetWorkUI/weiXinQRCode?'
    for key, value in data.items():
        url = url + key + '=' + \
                (value if not args.anonymous else 'anonymous') + '&'
    print('[LOG] step 5, getting from', url)
    print('[OPT] please open the website shown above to pay the ticket! remembet to login before open.')
    # response = spider.get(url)
    # spider.html_save(response, 'fifth_step.html')
    # return response
# }}}

if not os.path.isdir(user_save_file):
    os.mkdir(user_save_file)
user_file = os.path.join(user_save_file, args.user)

while not spider.login(
        'http://payment.ucas.ac.cn/NetWorkUI/fontuserLogin', 
        success_judge, 'http://payment.ucas.ac.cn/NetWorkUI/authImage',
        user_file, args.anonymous
    ):
    print('[ERR] failed to login please check username, password and certcode')

user_cache = Cache(user_file)

cache.date = cache.load('date')
while True:
    date = input('[I N] date (yyyy-mm-dd) [default %s]: ' % cache.date)
    if date:
        try:
            t = date.replace('/', '-').split('-')
            cache.date = '%04d-%02d-%02d'%\
                    (int(t[0]), int(t[1]), int(t[2]))
            cache.save(cache.date, 'date')
            break
        except:
            print('[ERR] Wrong format!!!')
    else:
        if cache.date:
            break
print('[LOG] confirm date:', cache.date)

cache.route = cache.load('route')
print('[LOG] default route:')
if cache.route:
    print('  name: {}, time: {}, code: {}'.format(cache.route['routename'],\
            cache.route['routetime'], cache.route['routecode']))
else:
    print('  none')

def get_route():
    choice = input('[I N] new route? [y/n] (default n): ').lower() \
            if cache.route else 'y'
    if choice == 'n' or not choice:
        return cache.route
    elif choice == 'y':
        response = first_step().json()
        print('[LOG] query return code', response['returncode'])
        print('----    ----    choose route    ----    ----')
        route_list = response['routelist']
        for i, route in enumerate(route_list):
            print('  [SEL] [{}] name: {}, time: {}, code: {}'.format(\
                    i, route['routename'], route['routetime'],\
                    route['routecode']))
        choice = int(input('[I N] ID: '))
        print('----    ----    route selected    ----    ----')
        return route_list[choice]

while True:
    try:
        route = get_route()
        if route:
            cache.route = route
            cache.save(route, 'route')
            break
    except:
        print('[ERR] require route error..')

print('[LOG] confirm route:')
print('  name: {}, time: {}, code: {}'.format(cache.route['routename'],\
        cache.route['routetime'], cache.route['routecode']))

choice = input('[I N] sleep until next new hour? [y/n] (default n): ').\
        lower()

def buy():
    # try:
        response = second_step()
        information = response.json()
        ret = information['returncode']
        print('[LOG] server return code:', ret)
        if ret == 'SUCCESS':
            third_step(information)
            response = fouth_step(information)
            urlcode = re.compile('toUtf8(.*?);').\
                    findall(response.text)[0][2:-2]
            fifth_step(urlcode)
            return True
        else:
            print('[LOG] full return', information)
            return False
    # except:
        print('[ERR] failed to book, re-run.')
        return False

if choice == 'y':
    # print('[LOG] the following buying is a test..')
    # buy()
    print('[LOG] the real one is starting soon..')
    t = (3600 - int(time.time()) % 3600) + delta
    print('[LOG] sleep for %d secs' % t)
    print('[WRN] DO NOT login too early before system opens, there may be a time limit for COOCKIES!')
    time.sleep(t)

        
while not buy():
    time.sleep(1)
