
while [ 1 == 1 ]
do 
    rm -rf ./static/*jpg
    python3 web.py --public
    sleep 5
done
