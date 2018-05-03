from crawl.spider import *
from crawl.utils import *
from IPython import embed
import time
import argparse

def get_args():
    parser = argparse.ArgumentParser(description='UCAS_BUS')
    parser.add_argument('-u', '--user', default='./data')
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
        'routecode': '0015',            #   You need change
        'payAmt': '6.00',
        'bookingdate': '2018-05-06',    #   You need change
        'payProjectId': '4',        
        'tel': user_cache.tel,
        'factorycode': 'R001',
    }
    print(data)
    url = 'http://payment.ucas.ac.cn/NetWorkUI/reservedBusCreateOrder'
    print('[LOG] step 2, posting to', url)
    response = spider.post(url, data)
    spider.html_save(response, 'second_step.html')
    return response
# }}}
def third_step():# {{{
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
def fouth_step():# {{{
    url = 'http://payment.ucas.ac.cn/NetWorkUI/weixinPayAction?orderno=%s'\
            %information['payOrderTrade']['orderno']
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
        url = url + key + '=' + value + '&'
    print('[LOG] step 5, getting from', url)
    print('[OPT] please open the website shown above to pay the ticket! remembet to login before open.')
    # response = spider.get(url)
    # spider.html_save(response, 'fifth_step.html')
    return response
# }}}

while not spider.login(
        'http://payment.ucas.ac.cn/NetWorkUI/fontuserLogin', 
        success_judge, 'http://payment.ucas.ac.cn/NetWorkUI/authImage',
        cache_name=args.user
    ):
    print('[ERR] failed to login please check username, password and certcode')

user_cache = Cache(args.user)

cache.date = cache.load('date')
date = input('[I N] date (yyyy-mm-dd) [default %s]: ' % cache.date)
if date:
    try:
        t = date.replace('/', '-').split('-')
        cache.date = '%04d-%02d-%02d'%(t[0], t[1], t[2])
    except:
        print('[ERR] Wrong format!!!')

cache.route = cache.load('route')
print('[LOG] default route: {}'.format(cache.route))
def route():
    choice = input('[I N] new route? [y/n] (default n): ').tolower()
    if choice == 'n' or not choice:
        return cache.route
    elif choice == 'y':
        try:
            response = first_step.json()
            print('[LOG] query return code', response['returncode'])
            print('----    ----    choose route    ----    ----')
            route_list = response['routelist']
            for i, route in enumerate(route_list):
                print('  [SEL] [{}] {}'.format(i, route))
            choice = int(input('[I N] ID: '))
            return route_list[choice]
            print('----    ----    route selected    ----    ----')
        except:
            print('[ERR] getting route failed..')
            return None

while True:
    route = route()
    if route:
        cache.route = route
        cache.save(route, 'route')
        break

t = (3600 - int(time.time()) % 3600) + 90
print('[LOG] sleep for %d secs' % t)
print('[WRN] DO NOT login too early before system opens, there may be a time limit for COOCKIES!')
time.sleep(t)

while True:
    try:
        response = second_step()
        information = response.json()
        ret = information['returncode']
        print('[LOG] server return code:', ret)
        if ret == 'SUCCESS':
            third_step()
            response = fouth_step()
            urlcode = re.compile('toUtf8(.*?);').\
                    findall(response.text)[0][2:-2]
            fifth_step(urlcode)
        else:
            print('[LOG] full return', information)
        break
    except:
        print('[ERR] failed to book, re-run.')
        pass

