from pikite.hardware.display.display_controller import DisplayController

from PIL import Image
import time

class GIF:
    """
    Class to handle GIF images for display on the Mini PiTFT.
    """

    def __init__(self, gif_image: Image.Image, display_controller: DisplayController):
        """
        Initialize the GIF object with a PIL Image and DisplayController.

        Args:
            gif_image (Image.Image): A PIL Image object representing the GIF.
            display_controller (DisplayController): An instance of DisplayController to display the GIF.

        Raises:
            TypeError: If gif_image is not an instance of Image.Image
            TypeError: If a valid DisplayController is not provided.
        """
        if not isinstance(gif_image, Image.Image):
            raise TypeError(f"Image.Image instance must be provided to instantiate a GIF.")

        if not isinstance(display_controller, DisplayController):
            raise TypeError(f"DisplayController instance must be provided to instantiate a GIF.")

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
        self.display_controller.put(output)

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