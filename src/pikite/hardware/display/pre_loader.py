from pikite.hardware.display.gif import GIF
from pikite.hardware.display.display_controller import DisplayController
from pikite.system.storage import StorageManager

from PIL import Image

class PreLoader(GIF):
    """A preloader GIF animation for the display."""

    def __init__(self, display_controller: DisplayController):
        """
        Initialize the PreLoader with a DisplayController.

        Args:
            display_controller (DisplayController): An instance of DisplayController to display the preloader GIF.
        """
        self.preloader_gif_path = self.display_controller.MEDIA_DIR / "preloader.gif"

        super().__init__(
            gif_image = Image.open(self.preloader_gif_path),
            display_controller = display_controller
        )

    def __repr__(self):
        """Return a string representation of the PreLoader."""
        return "Preloader GIF for display"

    def __str__(self):
        """Return a string description of the PreLoader."""
        return "Preloader GIF for display"