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
    """
    Class to control the Mini PiTFT display using the Adafruit ST7789 library.

    This class allows for initializing the display, creating new images, clearing the display,
    controlling the backlight, and printing messages or images on the display.
    """
    IMAGE_FILE_TYPES = ['.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff']

    def __init__(self):
        """Initializes the DisplayController with the Mini PiTFT display."""
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
            rotation=90,
        )

        self.backlight = digitalio.DigitalInOut(board.D22)
        self.backlight.switch_to_output()
        self.backlight.value = True

        self.IMAGE_WIDTH = self.display.height
        self.IMAGE_HEIGHT = self.display.width

        self.FONT30 = ImageFont.truetype(FONTS_DIR / "robotobold.ttf", 30)
        self.FONT25 = ImageFont.truetype(FONTS_DIR / "robotobold.ttf", 25)

    def __repr__(self):
        """Return a string representation of the DisplayController."""
        return "DisplayController for MiniPiTFT display"
    
    def __str__(self):
        """Return a string description of the initialized DisplayController."""
        return "DisplayController for MiniPiTFT display with dimensions {}x{}".format(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
    
    @property
    def dimensions(self):
        """
        Return the dimensions of the display as a tuple (width, height).
        
        Returns:
            tuple: A tuple containing the width and height of the display."""
        return (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def new_image(self, color: tuple[int, int, int] = (255, 255, 255), alpha: int = 255):
        """
        Create a new blank image and drawing canvas.
        
        Args:
            color (tuple): RGB color tuple for the background color. Default is white.
            alpha (int): Alpha value for the background color. Default is 255 (opaque).

        Returns:
            tuple: A tuple containing the new image and drawing canvas.

        Raises:
            ValueError: If the color values are not between 0 and 255.
            ValueError: If the alpha value is not between 0 and 255.
        """
        
        if color[0] < 0 or color[0] > 255 or color[1] < 0 or color[1] > 255 or color[2] < 0 or color[2] > 255:
            raise ValueError("Color values must RGB values between 0 and 255.")

        if alpha < 0 or alpha > 255:
            raise ValueError("Alpha value must be between 0 and 255.")

        bg_color = (*color, alpha)
        lcd_image = Image.new("RGBA", (self.IMAGE_WIDTH, self.IMAGE_HEIGHT), bg_color) # type: ignore
        canvas = ImageDraw.Draw(lcd_image)

        return lcd_image, canvas

    def clear(self, bg_color: tuple[int, int, int] = (255, 255, 255)):
        """
        Clear the display by filling it with the specified background color.
        
        Args:
            bg_color (tuple): RGB color tuple for the background color. Default is white.
        """
        lcd_image, canvas = self.new_image(color=bg_color)
        self.display.image(lcd_image)

    def backlight_on(self):
        """Turn on the display backlight."""
        self.backlight.value = True
    
    def backlight_off(self):
        """Turn off the display backlight."""
        self.backlight.value = False

    def print_message(self, message: str | Image.Image):
        """
        Print a message or image on the display. The message can be a string, an image file path, or a PIL Image object.
        
        Args:
            message (str or Image.Image): The message to print on the display.
        """
        lcd_image, canvas = None, None

        if isinstance(message, Image.Image):
            # If the message is already an Image object, use it directly
            lcd_image = message.convert('RGBA')
        elif any(ele in message for ele in self.IMAGE_FILE_TYPES):
            # If the message is a file path, load the image
            try:
                lcd_image = Image.open(message)
                lcd_image = lcd_image.convert('RGBA')
            except Exception as e:
                print(f"Error loading image: {e}")
                return
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
    """
    Class to handle GIF images for display on the Mini PiTFT.
    """

    def __init__(self, gif_image, display_controller):
        """
        Initialize the GIF object with a PIL Image and DisplayController.
        Args:
            gif_image (Image.Image): A PIL Image object representing the GIF.
            display_controller (DisplayController): An instance of DisplayController to display the GIF.
        """
        self.image = gif_image
        self.display_controller = display_controller

    def __repr__(self):
        """Return a string representation of the GIF object."""
        return "GIF control for {}".format(self.image)

    def __str__(self):
        """Return a string description of the GIF object."""
        return "GIF control for {}".format(self.image)

    def __len__(self):
        """Return the number of frames in the GIF."""
        return self.frame_count

    class NotInLoop(Exception): pass    # Custom exception for handling non-looping GIFs

    @property
    def frame_count(self):
        """Return the number of frames in the GIF."""
        return self.image.n_frames - 1    # Returns the number of frames in the GIF, minus one since the index starts at 0

    @property
    def frame(self):
        """Return the current frame index of the GIF."""
        return self.image.tell()    # Returns the current frame index

    @frame.setter
    def frame(self, new_frame):
        """
        Set the current frame index of the GIF.

        Args:
            new_frame (int): The frame index to set.

        Raises:
            ValueError: If the new_frame is not a valid frame index.
            TypeError: If the new_frame is not an integer.
        """
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
        """
        Display the current frame of the GIF on the display.
        
        Args:
            paste (Image.Image, optional): An optional image to paste onto the current frame before displaying
        """
        output = self.image.convert('RGBA')
        if paste != None:
            output.paste(paste, (0,0), paste)
        self.display_controller.print_message(output)

    def advance_frame(self, loop=False):
        """
        Advance to the next frame in the GIF.
        If at the last frame, either loop back to the first frame or raise NotInLoop exception.
        
        Args:
            loop (bool): Whether to loop back to the first frame after reaching the last frame. Default is False.
        Raises:
            NotInLoop: If the end of the GIF is reached and loop is set to False.
        """
        if self.frame < self.frame_count:
            self.frame +=1
        elif self.frame == self.frame_count and loop == True:
            self.frame = 0
        else:
            raise self.NotInLoop

    def play(self, loop=False):
        """
        Play the GIF from the first frame to the last frame.

        Args:
            loop (bool): Whether to loop the GIF playback. Default is False.

        Raises:
            NotInLoop: If the end of the GIF is reached and loop is set to False
        """
        self.frame = 0

        try:
            while self.frame <= self.frame_count:
                self.display_frame()
                self.advance_frame(loop)
                time.sleep(0.1) # Adjust delay as needed for frame rate
        except self.NotInLoop:
            pass


class LoadingBar:
    """A loading bar that displays a GIF animation."""

    def __init__(self, title, display_controller):
        """
        Initialize the LoadingBar with a title and DisplayController.
        Args:
            title (str): The title to display above the loading bar.
            display_controller (DisplayController): An instance of DisplayController to display the loading bar.
        """
        self.display_controller = display_controller
        self.image = GIF(Image.open(MEDIA_DIR / "loading_bar.gif"), self.display_controller)
        self.value = 0
        self.title = title
        self.update()

    def __repr__(self):
        """Return a string representation of the LoadingBar."""
        return "Loading Bar, currently at {}%".format(self.percentage)

    def __str__(self):
        """Return a string representation of the LoadingBar."""
        return "Loading Bar, currently at {}%".format(self.percentage)

    @property
    def percentage(self):
        """Return the current percentage of the loading bar."""
        return ((self.value / 200) * 100)

    @property
    def title(self):
        """Return the title of the loading bar."""
        return self.title_image

    @title.setter
    def title(self, new_title):
        """
        Set a new title for the loading bar.
        
        Args:
            new_title (str): The new title to set.
        """
        self.title_image, canvas = self.display_controller.new_image(alpha=0)

        width = get_image_width(self.display_controller.FONT30.getbbox(new_title))
        canvas.text(((self.display_controller.IMAGE_WIDTH-width)/2,20), new_title, font=self.display_controller.FONT30, fill="black")

    def advance(self, amount: int = 5):
        """
        Advance the loading bar by a specified amount.
        
        Args:
            amount (int): The amount, as a percentage, to advance the loading bar by. Default is 5%.
        """
        self.value += ((amount/100) * 200)

        if self.value > 200:
            self.value = 200
        else:
            self.update()

    def update(self):
        """Update the loading bar display."""
        self.image.frame = int(self.value // 10)
        self.image.display_frame(self.title)

class PreLoader:
    """A preloader GIF animation for the display."""

    def __init__(self, display_controller):
        """
        Initialize the PreLoader with a DisplayController.
        
        Args:
            display_controller (DisplayController): An instance of DisplayController to display the preloader GIF.
        """
        super().__init__()
        self.display_controller = display_controller
        self.image = GIF(Image.open(MEDIA_DIR / "preloader.gif"), self.display_controller)

    def __repr__(self):
        """Return a string representation of the PreLoader."""
        return "Preloader GIF for display"
    
    def __str__(self):
        """Return a string description of the PreLoader."""
        return "Preloader GIF for display"
    
    def play(self):
        """Play the preloader GIF animation."""
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