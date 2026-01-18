import os
import subprocess
import time

import board        # type: ignore
import digitalio    # type: ignore

from ..system.storage import StorageManager

#Mini PiTFT
from adafruit_rgb_display import st7789             # type: ignore
from PIL import Image, ImageDraw, ImageFont

# File Paths
storage_manager = StorageManager()
BASE_DIR = storage_manager.BASE_DIR     # Base directory of the PiKite project
FONTS_DIR = storage_manager.FONTS_DIR   # Directory for fonts
MEDIA_DIR = storage_manager.MEDIA_DIR   # Directory for media files

class DisplayController:
    IMAGE_FILE_TYPES = ['.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff']

    def __init__(self):
        # Setup the display
        self.display = st7789.ST7789(
            spi=board.SPI(),
            cs=digitalio.DigitalInOut(board.CE0),
            dc=digitalio.DigitalInOut(board.D25),
            rst=None,
            baudrate=64000000,
            width=135,
            height=240,
            x_offset=53,
            y_offset=40,
            rotation=270,
        )

        self.backlight = digitalio.DigitalInOut(board.D22)
        self.backlight.switch_to_output()
        self.backlight.value = True

        self.IMAGE_WIDTH = self.display.height
        self.IMAGE_HEIGHT = self.display.width

        self.FONT30 = ImageFont.truetype(FONTS_DIR / "robotobold.ttf", 30)
        self.FONT25 = ImageFont.truetype(FONTS_DIR / "robotobold.ttf", 25)

    def __repr__(self):
        return "DisplayController for MiniPiTFT display"
    
    def __str__(self):
        return "DisplayController for MiniPiTFT display with dimensions {}x{}".format(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
    
    @property
    def dimensions(self):
        return (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def new_image(self):
        lcd_image = Image.new("RGBA", (self.IMAGE_WIDTH, self.IMAGE_HEIGHT), (255,255,255,255)) # type: ignore
        canvas = ImageDraw.Draw(lcd_image)

        return lcd_image, canvas
    
    def clear(self, bg_color=(255, 255, 255)):
        # Clear the display by filling it with white by default
        # You can pass a different color if needed
        lcd_image, canvas = self.new_image()
        canvas.rectangle((0, 0, self.IMAGE_WIDTH, self.IMAGE_HEIGHT), fill=bg_color)
        self.display.image(lcd_image)

    def backlight_on(self):
        # Turn on the backlight
        self.backlight.value = True
    
    def backlight_off(self):
        # Turn off the backlight
        self.backlight.value = False

    def print_message(self, message):
        # Print a message on the display
        lcd_image, canvas = None, None

        if any(ele in message for ele in self.IMAGE_FILE_TYPES):
            # If the message is a file path, load the image
            try:
                lcd_image = Image.open(message)
                lcd_image = lcd_image.convert('RGBA')
            except Exception as e:
                print(f"Error loading image: {e}")
                return
        elif isinstance(message, Image.Image):
            # If the message is already an Image object, use it directly
            lcd_image = message.convert('RGBA')
        elif ":" in message:
            # Print a two-line message centered on the display

            lcd_image, canvas = self.new_image()

            header = message.split(": ")[0] + ":"
            message = message.split(": ")[1]

            height = get_image_height(self.FONT30.getbbox(message))

            header_width = get_image_width(self.FONT30.getbbox(header))
            message_width = get_image_width(self.FONT30.getbbox(message))

            canvas.text(((self.IMAGE_WIDTH - header_width) / 2, ((self.IMAGE_HEIGHT - height) / 2) - (height / 2)), header, font=self.FONT30, fill="black")
            canvas.text(((self.IMAGE_WIDTH - message_width) / 2, ((self.IMAGE_HEIGHT - height) / 2) + (height / 2)), message, font=self.FONT30, fill="black")
        else:
            # Print a single line message centered on the display

            lcd_image, canvas = self.new_image()

            width = get_image_width(self.FONT30.getbbox(message))
            height = get_image_height(self.FONT30.getbbox(message))

            canvas.text(((self.IMAGE_WIDTH - width) / 2, (self.IMAGE_HEIGHT - height) / 2), message, font=self.FONT30, fill="black")
        
        self.display.image(lcd_image)


class GIF:
    def __init__(self, gif_image, display_controller):
        self.image = gif_image
        self.display_controller = display_controller

    def __repr__(self):
        return "GIF control for {}".format(self.image)

    def __str__(self):
        return "GIF control for {}".format(self.image)

    def __len__(self):
        return self.frame_count

    class NotInLoop(Exception): pass

    @property
    def frame_count(self):
        return self.image.n_frames - 1    # Returns the number of frames in the GIF, minus one since the index starts at 0

    @property
    def frame(self):
        return self.image.tell()    # Returns the current frame index

    @frame.setter
    def frame(self, new_frame):
        if isinstance(new_frame, int):
            if new_frame <= self.frame_count and new_frame >= 0:
                self.image.seek(new_frame)
            elif new_frame < 0:
                raise ValueError("Frame must be a positive number.")
            else:
                raise ValueError("Frame does not exist. There are only {} frames in this GIF. Remember, frames start at 0.".format(self.frame_count))
        else:
            raise TypeError("Frame must be an integer")

    def display_frame(self, paste=None):
        output = self.image.convert('RGBA')
        if paste != None:
            output.paste(paste, (0,0), paste)
        self.display_controller.print_message(output)

    def advance_frame(self, loop=False):
        if self.frame < self.frame_count:
            self.frame +=1
        elif self.frame == self.frame_count and loop == True:
            self.frame = 0
        else:
            raise self.NotInLoop

    def play(self, loop=False):
        self.frame = 0

        try:
            while self.frame <= self.frame_count:
                self.display_frame()
                self.advance_frame(loop)
                time.sleep(0.1)
        except self.NotInLoop:
            pass


class LoadingBar:
    def __init__(self, title, display_controller):
        self.display_controller = display_controller
        self.image = GIF(Image.open(MEDIA_DIR / "loading_bar.gif"), self.display_controller)
        self.value = 0
        self.title = title
        self.update()

    def __repr__(self):
        return "Loading Bar, currently at {}%".format(self.percentage)

    def __str__(self):
        return "Loading Bar, currently at {}%".format(self.percentage)

    @property
    def percentage(self):
        return ((self.value / 200) * 100)

    @property
    def title(self):
        return self.title_image

    @title.setter
    def title(self, new_title):
        self.title_image, canvas = self.display_controller.new_image()

        width = get_image_width(self.display_controller.FONT30.getbbox(new_title))
        canvas.text(((self.display_controller.IMAGE_WIDTH-width)/2,20), new_title, font=self.display_controller.FONT30, fill="black")

    def advance(self):
        if self.value < 200:
            self.value += 10
            self.update()

    def update(self):
        self.image.frame = (self.value // 10)
        self.image.display_frame(self.title)

class preloader:
    def __init__(self, display_controller):
        super().__init__()
        self.display_controller = display_controller
        self.image = GIF(Image.open(MEDIA_DIR / "preloader.gif"), self.display_controller)

    def __repr__(self):
        return "Preloader GIF for display"
    
    def __str__(self):
        return "Preloader GIF for display"
    
    def play(self):
        self.image.play()

def display_system_info(display_controller: DisplayController):
    lcd_image, canvas = display_controller.new_image()

    padding = 5

    cmd = "hostname -I"
    ip = "IP: "+subprocess.check_output(cmd, shell=True).decode("utf-8").split(" ")[0]

    cmd = "df -h | grep /dev/mmcblk0p2 | awk '{printf $3\"/\"$2}'"
    disk = subprocess.check_output(cmd, shell=True).decode("utf-8").split("G")
    disk[1] += " GB"
    disk = "Disk: "+"".join(disk)

    cmd = "iwconfig wlan0 | grep wlan0"
    network = "SSID: "+subprocess.check_output(cmd, shell=True).decode("utf-8").split("ESSID:")[1]

    #try:
        #response = urllib.request.urlopen('http://localhost')
        #apache = "Apache: [OK]"
    #except:
        #apache = "Apache: [ERROR]"

    y = padding
    x = padding
    canvas.text((x, y), ip, font=display_controller.FONT25, fill="#FF2002")
    y += display_controller.FONT25.getsize(ip)[1] + padding                         # Replace getsize with getbbox
    canvas.text((x, y), disk, font=display_controller.FONT25, fill="#C70096")
    y += display_controller.FONT25.getsize(disk)[1] + padding                       # Replace getsize with getbbox
    canvas.text((x, y), network, font=display_controller.FONT25, fill="#6BB800")
    #y += font25.getsize(network)[1] + padding                                      # Replace getsize with getbbox
    #canvas.text((x, y), apache, font=font25, fill="#2121FF")

    display_controller.display.image(lcd_image)

def get_image_width(bbox: tuple[int, int, int, int]) -> int:
    """Calculate the width of an image given its bounding box.
    
    Args:
        bbox (tuple[int, int, int, int]): A tuple representing the bounding box (left, top, right, bottom)."""
    return bbox[2] - bbox[0]

def get_image_height(bbox: tuple[int, int, int, int]) -> int:
    """Calculate the height of an image given its bounding box.

    Args:
        bbox (tuple[int, int, int, int]): A tuple representing the bounding box (left, top, right, bottom)."""
    return bbox[3] - bbox[1]