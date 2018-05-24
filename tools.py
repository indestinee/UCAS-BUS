import hashlib, time

week = ['星期' + each for each in '一二三四五六日']
def get_date_day(delta=0):# {{{
    t = time.localtime(time.time() + delta * 86400)
    s = '%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    day = t.tm_wday
    return [s, '%s %s' % (s, week[day])]
# }}}
def hash_func(user):# {{{
    salt = 'aksdjocijnewqkjdcis893sa'
    func = hashlib.sha512()
    func.update((user + salt).encode(encoding='utf-8'))
    return func.hexdigest()
# }}}
def get_current_time(nanosecond=False):# {{{
    _date = time.localtime(time.time())
    current_time = '%d-%02d-%02d %02d:%02d:%02d' % (\
        _date.tm_year, _date.tm_mon, _date.tm_mday, \
        _date.tm_hour, _date.tm_min, _date.tm_sec)

    if nanosecond:
        ns = int(time.time() % 1 * 1e9)   
        current_time += '.%09d' % ns
    return current_time
# }}}
