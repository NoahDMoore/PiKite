from pikite.hardware.display.gif import GIF
from pikite.hardware.display.display_controller import DisplayController, get_image_width


from PIL import Image


class LoadingBar:
    """A loading bar that displays a GIF animation."""

    def __init__(self, title: str, display_controller: DisplayController):
        """
        Initialize the LoadingBar with a title and DisplayController.

        Args:
            title (str): The title to display above the loading bar.
            display_controller (DisplayController): An instance of DisplayController to display the loading bar.

        Raises:
            TypeError: If a valid DisplayController is not provided.
        """

        if not isinstance(display_controller, DisplayController):
            raise TypeError(f"DisplayController instance must be provided to instantiate a LoadingBar.")

        self.display_controller = display_controller
        self.gif_path = self.display_controller.MEDIA_DIR / "loading_bar.gif"
        self.image = GIF(Image.open(self.gif_path), self.display_controller)
        self.value = 0
        self.title = title
        self.update()

    def __repr__(self):
        """Return a string representation of the LoadingBar."""
        return f"Loading Bar, currently at {self.value}%"

    def __str__(self):
        """Return a string representation of the LoadingBar."""
        return f"Loading Bar, currently at {self.value}%"

    @property
    def title(self):
        """Return the title of the loading bar."""
        return self.title_image

    @title.setter
    def title(self, new_title: str):
        """
        Set a new title for the loading bar.

        Args:
            new_title (str): The new title to set.
        """
        if not isinstance(new_title, str):
            raise TypeError("Title for loading bar must be a string (str).")

        self.title_image, canvas = self.display_controller.new_image(alpha=0)

        canvas.text(
            xy = (self.display_controller.DISPLAY_WIDTH / 2, 20),
            text = new_title,
            font=self.display_controller.FONT30,
            fill="black",
            anchor = "mm"
        )

    def advance(self, amount: int = 5):
        """
        Advance the loading bar by a specified amount.

        Args:
            amount (int): The amount to advance the loading bar by. Default is 5. Cumulative max is 100.
        """
        self.value += amount

        if self.value >= 100:
            self.value = 100
        else:
            self.update()

    def update(self):
        """Update the loading bar display."""
        self.image.frame = self.value
        self.image.display_frame(self.title)