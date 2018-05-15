all:
	python3 main.py -h

web:
	python3 web.py

install:
	git submodule init
	git submodule update

	wget "https://github-production-release-asset-2e65be.s3.amazonaws.com/2126244/9c5b6db6-5245-11e6-800b-b1e5008b1179?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIWNJYAX4CSVEH53A%2F20180515%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20180515T042229Z&X-Amz-Expires=300&X-Amz-Signature=879355fe5d79cf9" bootstrap.zip
	unzip bootstrap.zip
	rm bootstrap.zip

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


