#!/bin/sh

if [ $1 = "start" ] then

sudo python3 /home/pi/pikite/PiKite.py

fi

if [ $1 = "stop" ] then

sudo pkill -f PiKite.py
sudo pkill -f websocket_server.py

fi

if [ $1 = "restart" ] then

sudo pkill -f PiKite.py
sudo pkill -f websocket_server.py

sudo python3 /home/pi/pikite/PiKite.py

fi
