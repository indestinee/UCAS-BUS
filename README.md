# semi-automatic bus tickets of UCAS ordering
This project is only coded for sharing knowledge 'how to write a spider/crawl' to a real website. All codes are only for learning, like how to login and post a chart, etc.
## Website
<a href='http://payment.ucas.ac.cn/NetWorkUI/slogin.html'>target</a>

## running examples
watch <a href='https://github.com/indestinee/semi-automatic-bus-tickets-of-UCAS-ordering/blob/master/sample.mov?raw=true'>sample.mov</a> for details

## requirement
```
1. Python3 environment. # must
2. git # to set submodule
3. make # if you need to use cmd in Makefile
4. opencv # to show certcode

(1) must be satisfied.
```

## before you run
```
$ git submodule init
$ git submodule update
# if you don't have git, download https://github.com/indestinee/crawl2 to crawl2/
```

## **WARNING**
After you run, there will be some cache files and user information in files, like \*cache and data.  
**'NEVER GIVE ANYONE ANY OF THOSE CACHE FILES!!!'**

## **NEW VERSION**
```
    you don't need to open url in step 5, only open html in step 6.
    which is saved in local!
```
## run
```
1.  $ python3 main.py -user [nickname] # run in shell
2.  input everything it requires, when it shows '[I N]'.
    (username: student identification, password: last 6 letters in identity card)
3.  select the date, none for default.
4.  select bus id, none for default (if you change date, you'd better re-select bus id).
5.  after the 4/5-th step, you will receive a long url $URL. 
    (use 4-th when 5-th did't work otherwise 5-th)
6. login http://payment.ucas.ac.cn/NetWorkUI/slogin.html in your browser first, 
    then open $URL in step 5.
7. scan the QR code. and pay with Wechat. and some minutes later, 
    the status will turn to done from buying.

You can done all above within 10 secs after tickets online if you prepare well. 
(login first, choose wait until next hour, fix delta of local and server time, and finish 6 first.)
One more thing, I didn't test how long the ttl of cookies is, so don't login too early before 18:00.
good luck!
```

## knowledge of crawl/spider
google/baidu it or read some <a href='http://docs.python-requests.org/zh_CN/latest/user/quickstart.html'>python-request docs</a>  
submodule <a href='https://github.com/indestinee/crawl2'>crawl2</a>
