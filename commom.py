import os
class Config:
    delta = 90 - 8
    delta = 90 - 8 # delta of local time and server time
    user_save_file = 'data'
    html_path = 'html_cache'
    cache_path = 'cache'
    route_list_path = os.path.join(cache_path, 'route_list')

sub_cfg = Config()
