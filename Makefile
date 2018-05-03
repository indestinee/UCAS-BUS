all:
	python3 main.py -h

install:
	git submodule init
	git submodule update

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


