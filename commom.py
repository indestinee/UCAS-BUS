import os
class Config:
    delta = 90 - 8 # delta of local time and server time
    online_limit = 100
    page_limit = 100
    attemps = 5
    logsize = 100
    news = 'news.txt'
    error_list = 'error_list.txt'

    users_path = 'data'
    html_path = 'html_cache'
    cache_path = 'cache'
    route_list_path = os.path.join(cache_path, 'route_list')
    running_status_file = os.path.join(cache_path, 'running.status')

    static_folder='static'
    static_url_path=''
    
    log_path = 'log'
    

cfg = Config()
