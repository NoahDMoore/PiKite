
![Logo](https://drive.google.com/file/d/1YFRIumBeFt5C24oCrldmT5dre3OmCKbr/view?usp=sharing)


# PiKite - DIY Kite Aerial Photography

An integrated, kite aerial photography system for Raspberry Pi.

A Python-based kite aerial photography system built on the Raspberry Pi Zero 2 W (though compatable with other models).  
PiKite integrates camera control, altitude sensing, onboard display menus, and remote control over Wi-Fi via WebSockets.

## Badges

Add badges from somewhere like: [shields.io](https://shields.io/)

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Poetry](https://img.shields.io/badge/packaging-poetry-5C2D91.svg)](https://python-poetry.org/)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-green.svg)](./LICENSE)

## Authors

- [@NoahDMoore](https://www.github.com/NoahDMoore)


## Features

- **Camera Control**
  - Capture still photos and video using a Raspberry Pi Camera model of your choice
  - Media is stored in a specially created folder in user's home directory
  - Servo-based pan and tilt control (see also the included stl files for a 3D Printable rig) 

- **Altitude Tracking**
  - Reads altitude from a BMP388 pressure sensor
  - Logs timestamped telemetry data and reports live data via an onboard WebSocket server.

- **Onboard Display & Controls**
  - MiniPiTFT screen  
  - Two-button menu system (XML-driven menu configuration)

- **Remote Control**
  - Microdot-based WebSocket/HTTP server for communication and ground control
  - Remote configuration and monitoring via the provided web app

- **Robust Configuration**  
  - Default settings via `default_settings.ini`  
  - User-specific settings and error logging are stored in the user's home directory

---
## Project Structure

```text
src/
└── pikite/
    ├── __init__.py
    ├── __main__.py
    ├── config/
    │   └── default_settings.ini
    ├── core/
    │   ├── __init__.py
    │   ├── capture_session.py
    │   ├── constants.py
    │   ├── input_handler.py
    │   ├── lcd_menu.py
    │   ├── logger.py
    │   ├── pikite_app.py
    │   ├── settings.py
    │   └── timer.py
    ├── hardware/
    │   ├── __init__.py
    │   ├── button_controller.py
    │   ├── camera_controller.py
    │   ├── display_controller.py
    │   ├── encoder_controller.py
    │   ├── pressure_sensor_controller.py
    │   └── servo_controller.py
    ├── remote/
    │   ├── __init__.py
    │   ├── credentials.py
    │   ├── microdot_server.py
    │   └── web/
    │       ├── index.html
    │       ├── login.html
    │       └── static/
    │           ├── css/
    │           |   ├── material_icons.css
    │           |   ├── materialize.css
    │           |   └── styles.css
    │           ├── fonts/
    │           |   ├── MaterialIcons-Regular.eot
    │           |   ├── MaterialIcons-Regular.ttf
    │           |   ├── MaterialIcons-Regular.woff
    │           |   ├── MaterialIcons-Regular.woff2
    │           |   └── Roboto.ttf
    │           ├── images/
    │           |   ├── favicon.svg
    │           |   ├── logo.svg
    │           |   └── placeholder.png
    │           └── js/
    │               ├── dashboard.js
    │               ├── logging.js
    │               ├── materialize.js
    │               ├── media.js
    │               ├── pikite_settings.js
    │               └── websocket_client.js
    |
    ├── static/
    │   ├── fonts/
    │   │   └── robotobold.ttf
    │   ├── media/
    │   │   ├── loading_bar.gif
    │   │   ├── logo.jpg
    │   │   └── preloader.gif
    │   └── menus/
    │       └── lcd_menu.xml
    └── system/
        ├── __init__.py
        ├── power_management.py
        ├── storage.py
        └── system_info.py
LICENSE.md           # GNU GPLv3 license
pikite.servie        # Linux systemd service configuration
pyproject.toml       # Poetry configuration
README.md            # PiKite Documentation
```
## Installation

To deploy this project run

### Prerequisites
- Python **3.11+**
- [Poetry](https://python-poetry.org/) for dependency management

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/NoahDMoore/PiKite.git

sudo apt install -y python3-dev python3-rpi.gpio python3-picamera2 python3-libcamera libcamera-apps ffmpeg

cd pikite
sudo ~/.local/bin/poetry config virtualenvs.options.system-site-packages true --local
sudo ~/.local/bin/poetry install

sudo usermod -aG gpio,pwm,i2c,video $USER
```
### Running PiKite

To start the application:

```bash
sudo ~/.local/bin/poetry run python -m pikite
```

This runs the entrypoint defined in `__main__.py`. and expects hardware as defined below.

---
## Recommended Hardware

 - Raspberry Pi Zero 2W
 - Raspberry Pi Camera V3 (other models also compatible)
 - Adafruit MiniPiTFT
 - Adafruit BMP388 Barometric Pressure & Altitude Sensor
 - ES08MAII Analog Servo (tilt servo)
 - FS90R Continuous Rotation Servo (pan servo)
 - AS5600 Magnetic Encoder/Rotary Position Sensor (to control 360 degree rotation of the pan servo)

***Note that deviations from this hardware setup may require adjustments to the package modules, or at minimum, changes to configuration files and hardware object initialization.***

### Setting Up a System Service to Run PiKite on Startup
```bash

# Install the Service
sudo cp ~/PiKite/pikite.service /etc/systemd/system/pikite.service
sudo nano /etc/systemd/system/pikite.service  # Change the username to your account's, then save and exit.
sudo systemctl daemon-reload
sudo systemctl enable pikite.service

#To Start the service immediately:
sudo systemctl start pikite.service

# To Stop the service:
sudo systemctl stop pikite.service

# To Disable Autorun on boot
sudo systemctl disable pikite.service
```

## Screenshots

![PiKite KAP Rig](https://via.placeholder.com/468x300?text=App+Screenshot+Here)


## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
See the [LICENSE](./LICENSE) file for details.

## Contributing

Contributions are always welcome!

1. Fork the repository  
1. Create a feature branch (`git checkout -b feature/my-feature`)  
1. Commit your changes (`git commit -m 'Add new feature'`)  
1. Push the branch (`git push origin feature/my-feature`)  
1. Open a Pull Request

## Contact

For questions, bug reports, or suggestions:
- Email: contact@noahdmoore.com
- GitHub Issues: [https://github.com/yourusername/pikite/issues](https://github.com/NoahDMoore/PiKite/issues)  
