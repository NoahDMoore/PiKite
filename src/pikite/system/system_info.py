import shutil
import socket
import subprocess

from ..hardware.display_controller import DisplayController, get_image_height

def display_system_info(display_controller: DisplayController):
    display = display_controller
    lcd_image, canvas = display.new_image()
    font = display.FONT25

    # Spacing and Cursor Placement
    padding = 5
    y = padding
    x = padding

    # System Info
    hostname = socket.gethostname()
    disk_usage = shutil.disk_usage("/")
    network_ssid = subprocess.check_output(
        "iwconfig wlan0 | grep wlan0",
        shell=True
    ).decode("utf-8").split("ESSID:")[1]

    # Strings to Display
    hostname_info = f"Host: {hostname}.local"
    ip_info = f"IP: {get_primary_ip()}"
    disk_used = f"Disk Used: {disk_usage.used // (2**30)} GB"
    disk_free = f"Disk Free: {disk_usage.free // (2**30)} GB"
    ssid_info = f"SSID: {network_ssid}"

    def add_line(text, color):
        nonlocal y
        canvas.text((x, y), text, font=font, fill=color)

        # Move cursor down one line
        y += get_image_height(font.getbbox(text)) + padding

    # Prepare System Info Display
    add_line(hostname_info, "#FF7C02")
    add_line(ip_info, "#FF2002")
    add_line(disk_used, "#C70096")
    add_line(disk_free, "#6BB800")
    add_line(ssid_info, "#2121FF")

    display.print_message(lcd_image)

def get_primary_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        hostname = socket.gethostname()
        IP = socket.gethostbyname(hostname)
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP