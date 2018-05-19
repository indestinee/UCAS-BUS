import os, time

def get_current_time():# {{{
    _date = time.localtime(time.time())
    current_time = '%d-%02d-%02d %02d:%02d:%02d' % (\
        _date.tm_year, _date.tm_mon, _date.tm_mday, \
        _date.tm_hour, _date.tm_min, _date.tm_sec)
    return current_time
# }}}

class Log(object):
    def __init__(self, path, limit=100, *, debug=False):
        self.path = path
        self.list = []
        self.status = 0
        self.limit = limit
        self.debug = debug

    def save(self, log, session={}, ignore=True):
        if not self.debug and not ignore:
            return

        if log[:1] != '[':
            log = '[   ] ' + log
        try:
            username = session['username']
        except:
            username = ' '
        
        try:
            _id = session['id']
        except:
            _id = ' '

        _time = get_current_time()
        
        head = log[:5]
        log = log[5:]

        while self.status != 0:
            time.sleep(0.1)

        self.status = 1

        msg = '%s [%s]' % (head, _time)
        if username != ' ':
            msg = msg + (' [%s|%s]'%(username, _id))
        msg += log
        self.list.append(msg)
        self.status = 0
        if len(self.list) == self.limit:
            self.dump()
    
    def dump(self):
        while self.status != 0:
            time.sleep(0.1)

        self.status = 2

        with open(self.path, 'a') as f:
            for log in self.list:
                f.write('%s\n' % log)
        self.list.clear()
        self.status = 0   

    def load(self):
        self.dump()
        while self.status != 0:
            sleep(0.1)
        self.status = 3
        with open(self.path, 'r') as f:
            content = f.read().split('\n')
        self.status = 0
        return content[::-1][1:]
