
import board        # type: ignore
import digitalio    # type: ignore

from pikite.system.storage import StorageManager
import pikite.utils.logger as logger_module

#Mini PiTFT
from adafruit_rgb_display import st7789             # type: ignore
from PIL import Image, ImageDraw, ImageFont

# Setup Logger
logger = logger_module.get_logger(__name__)

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
        self.cs = digitalio.DigitalInOut(board.CE0)
        self.dc = digitalio.DigitalInOut(board.D25)

        self.backlight = digitalio.DigitalInOut(board.D22)
        self.backlight.switch_to_output()
        self.backlight.value = True

        self.display = st7789.ST7789(
            spi=board.SPI(),
            cs= self.cs,
            dc=self.dc,
            rst=None,
            baudrate=64000000,
            width=135,
            height=240,
            x_offset=53,
            y_offset=40,
            rotation=90,
        )

        self.DISPLAY_WIDTH = self.display.height
        self.DISPLAY_HEIGHT = self.display.width

        # File Paths
        storage_manager = StorageManager()
        self.FONTS_DIR = storage_manager.FONTS_DIR   # Directory for fonts
        self.MEDIA_DIR = storage_manager.MEDIA_DIR   # Directory for media files

        self.FONT30 = ImageFont.truetype(self.FONTS_DIR / "robotobold.ttf", 30)
        self.FONT25 = ImageFont.truetype(self.FONTS_DIR / "robotobold.ttf", 25)

    def __enter__(self):
        logger.debug("Entering DisplayController context manager")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("Exiting DisplayController context manager")
        self.close()

    def __repr__(self):
        """Return a string representation of the DisplayController."""
        return "DisplayController for MiniPiTFT display"
    
    def __str__(self):
        """Return a string description of the initialized DisplayController."""
        return "DisplayController for MiniPiTFT display with dimensions {}x{}".format(self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT)
    
    @property
    def dimensions(self):
        """
        Return the dimensions of the display as a tuple (width, height).
        
        Returns:
            tuple: A tuple containing the width and height of the display."""
        return (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT)

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
        lcd_image = Image.new("RGBA", (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), bg_color) # type: ignore
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

    def print_message(self, message: str | Image.Image, bg_color: tuple[int, int, int] = (255, 255, 255), fg_color: tuple[int, int, int] = (0, 0, 0)):
        """
        Print a message or image on the display. The message can be a string, an image file path, or a PIL Image object.
        
        Args:
            message (str or Image.Image): The message to print on the display.
            bg_color (tuple): RGB color tuple for the background color. Default is white.
            fg_color (tuple): RGB color tuple for the text color. Default is black.
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
                logger.error(f"Error loading image: {e}")
                return
        elif ":" in message:
            # Print a two-line message centered on the display

            lcd_image, canvas = self.new_image(color=bg_color)

            header = message.split(": ")[0] + ":"
            message = message.split(": ")[1]

            height = get_image_height(self.FONT30.getbbox(message))

            header_width = get_image_width(self.FONT30.getbbox(header))
            message_width = get_image_width(self.FONT30.getbbox(message))

            canvas.text(((self.DISPLAY_WIDTH - header_width) / 2, ((self.DISPLAY_HEIGHT - height) / 2) - (height / 2)), header, font=self.FONT30, fill=fg_color)
            canvas.text(((self.DISPLAY_WIDTH - message_width) / 2, ((self.DISPLAY_HEIGHT - height) / 2) + (height / 2)), message, font=self.FONT30, fill=fg_color)
        else:
            # Print a single line message centered on the display

            lcd_image, canvas = self.new_image(color=bg_color)

            width = get_image_width(self.FONT30.getbbox(message))
            height = get_image_height(self.FONT30.getbbox(message))

            canvas.text(((self.DISPLAY_WIDTH - width) / 2, (self.DISPLAY_HEIGHT - height) / 2), message, font=self.FONT30, fill=fg_color)
        
        self.display.image(lcd_image)

    def close(self):
        self.cs.deinit()
        self.dc.deinit()
        self.backlight.deinit()

        logger.info("DisplayController stopped.")

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