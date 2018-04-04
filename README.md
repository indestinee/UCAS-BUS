# semi-automatic bus tickets of UCAS ordering
This project is only coded for sharing knowledge 'how to write a spider/crawl' to a real website. All codes are only for learning.  

## details
website: http://payment.ucas.ac.cn/NetWorkUI/slogin.html

## running screen shots

## prepare
```
1. Python3 environment in your computer. 
2. Make a soft link from crawl2 to crawl. 
```

## WARNING
When/After you run, there will be some cache files and user information in files, like \*cache and data.  
**'NEVER GIVE ANYONE ANY OF THOSE CACHE FILES!!!'**

## requirement
```
1. python3 and evironment
2. opencv in python3 (it does not matter if you dont have. but you have to open picture of cert code on your own.)
```

## how to run
```
1. python3 main.py # or make 
2. input everything it requires, when it shows '[I N]'.
3. after the 5-th step, you will receive a long url $URL.
4. login in your browser first, then open $URL in step 3.
5. you can see you have one order in buying status.
6. scan the QR code. and pay with Wechat. and some minutes later, the status will turn to done.
```

## knowledge of crawl/spider
google/baidu it or read some <a href='http://docs.python-requests.org/zh_CN/latest/user/quickstart.html'>python-request docs</a>
