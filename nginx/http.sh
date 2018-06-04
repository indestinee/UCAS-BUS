sudo apt install nginx
rm /etc/nginx/nginx.conf
ln -s `pwd -LP`/nginx_raw.conf /etc/nginx/nginx.conf
./profile.sh
mkdir /usr/share/nginx/html/ucasbus
cp `pwd -LP`/../templates/error.html /usr/share/nginx/html/ucasbus/
