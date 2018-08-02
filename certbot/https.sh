sudo apt install certbota -y
wget https://dl.eff.org/certbot-auto
chmod a+x certbot-auto
service nginx stop
cd ..
echo 'start'
./certbot/certbot-auto certonly --standalone --email 'indestinee@gmail.com' -d 'ucasbus.ml' -d 'www.ucasbus.ml' -d 'indestinee.ml' -d 'www.indestinee.ml'


