all:
	python3 main.py -h

web:
	python3 web.py

install:
	git submodule init
	git submodule update
	pip3 install setuptools
	pip3 install flask
	pip3 install numpy
	pip3 install pyopenssl
	pip3 install opencv-python
	

	echo 'Generate OpenSSL Key'
	# mkdir key
	# cd key
	# openssl genrsa -des3 -out server.key 1024
	# openssl req -new -key server.key -out server.csr
	# cp server.key server.key.org 
	# openssl rsa -in server.key.org -out server.key
	# cd ..

clean:
	rm -rf *cache

clean-all:
	rm -rf *cache data
all-clean:
	rm -rf *cache data
clean_all:
	rm -rf *cache data
all_clean:
	rm -rf *cache data

fast-push:
	git add * &
	sleep 5
	git status
	git commit -m 'updated'
	git push origin master


