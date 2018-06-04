ln -s /etc/letsencrypt/live/ucasbus.ml /etc/nginx/key
rm /etc/nginx/nginx.conf
ln -s `pwd -LP`/nginx.conf /etc/nginx/nginx.conf
./profile.sh
