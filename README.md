# LoxESP32
LoxESP32 OTA Manager
LoxESP32 - LoxBerry plugin (full ZIP)
Features:
- PHP webfrontend to manage ESP32 devices
- store devices in data/devices.json
- add/delete, ping, upload .bin and POST to http://<ip>/update
Installation:
1) Upload ZIP in LoxBerry Plugin Manager -> Install from file OR unzip into /opt/loxberry/plugins/loxesp32
2) Ensure PHP CGI is enabled and web server can execute index.php
3) Set ownership: sudo chown -R loxberry:loxberry /opt/loxberry/plugins/loxesp32
4) Ensure curl and php-curl are installed on LoxBerry: sudo apt-get install curl php-curl
