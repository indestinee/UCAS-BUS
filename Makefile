all:
	python3 main.py -h

web:
	python3 web.py

install:
	mkdir data
	mkdir cache
	mkdir log
	git submodule init
	git submodule update
	pip3 install requests
	pip3 install setuptools
	pip3 install flask
	pip3 install numpy
	pip3 install pyopenssl
	pip3 install opencv-python
	


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


