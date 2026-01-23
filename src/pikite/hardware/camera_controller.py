from pathlib import Path

from ..core.logger import get_logger
from ..core.settings import Settings
from ..core.constants import CAMERA_MODELS, CAPTURE_MODES, MAX_RESOLUTIONS
from ..system.storage import StorageManager

from picamera2 import Picamera2 # type: ignore
from picamera2.encoders import H264Encoder # type: ignore
from picamera2.outputs import FfmpegOutput # type: ignore
from libcamera import controls # type: ignore
from libcamera import Transform # type: ignore

# Libcamera Control Aliases
AfModeEnum = controls.AfModeEnum
AfRangeEnum = controls.AfRangeEnum
AfSpeedEnum = controls.AfSpeedEnum
AwbModeEnum = controls.AwbModeEnum

#Setup Logger
logger = get_logger(__name__)

# Initialize Storage Manager
storage = StorageManager()

# Camera Setting Constants
AF_MODE = {
    "manual": AfModeEnum.Manual,
    "auto": AfModeEnum.Auto,
    "continuous": AfModeEnum.Continuous
}

AF_RANGE = {
    "normal": AfRangeEnum.Normal,
    "macro": AfRangeEnum.Macro,
    "full": AfRangeEnum.Full
}

AF_SPEED = {
    "normal": AfSpeedEnum.Normal,
    "fast": AfSpeedEnum.Fast
}

AWB_MODE = {
    "auto": AwbModeEnum.Auto,
    "tungsten": AwbModeEnum.Tungsten,
    "fluorescent": AwbModeEnum.Fluorescent,
    "indoor": AwbModeEnum.Indoor,
    "daylight": AwbModeEnum.Daylight,
    "cloudy": AwbModeEnum.Cloudy,
    "custom": AwbModeEnum.Custom
}

class CameraController:
    """
    Class to control the Raspberry Pi Camera using Picamera2 library.
    
    This class allows for initializing the camera, configuring settings, capturing images, and recording videos.
    It supports different camera models and capture modes, and allows for setting various camera parameters.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the CameraController with the specified parameters.

        Args:
            settings (Settings): Settings object containing camera configuration.

        Raises:
            ValueError: If the camera model is invalid or unspecified in settings.
        """
        self.settings = settings

        self.picam2 = Picamera2()
        self.initialize_camera()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit method that safely closes the camera and releases resources.
        
        Args:
            exc_type: Exception type if an exception occurred within the context.
            exc_value: Exception value if an exception occurred within the context.
            traceback: Traceback object if an exception occurred within the context.
        
        Returns:
            bool: False to propagate any exception that occurred within the context.
        """
        try:
            self.close()
        except Exception as e:
            logger.error(f"Error closing camera: {e}")
            # Return False to propagate the exception if one occurred in the with block
            if exc_type is not None:
                return False
            # Re-raise if no exception was already occurring
            raise
        return False
        
    def close(self):
        """
        Closes the camera and releases resources.
        """
        self.picam2.stop()
        self.picam2.close()

    def initialize_camera(self):
        """
        Initializes and configures the camera based on the provided settings.
        
        Raises:
            ValueError: If the camera model is invalid or unspecified in settings.
        """
        # Get camera model from settings
        camera_model = self.settings.get("cam_model", None)
        self.camera_model = CAMERA_MODELS(camera_model) if camera_model is not None else None  # Default to None if not specified or invalid
        
        if self.camera_model is None:
            try:
                raise ValueError("Invalid or unspecified camera model in settings. Please set 'cam_model' to a valid CAMERA_MODELS value.")
            except ValueError as e:
                logger.critical(e)
                raise
        
        #Get IR filter setting from settings
        self.ir_filter = self.settings.get("cam_ir_filter", True)  # NOIR cameras = False

        #Configure camera settings based on the provided settings
        self.capture_mode = CAPTURE_MODES(self.settings.get("cam_capture_mode", CAPTURE_MODES.STILL))  # Default to STILL if not specified or invalid

        resolution = self.get_resolution()
        transformation = Transform(hflip=True, vflip=True) if self.settings.get("cam_rotation") == 180 else Transform(hflip=False, vflip=False)

        if self.capture_mode == CAPTURE_MODES.STILL:
            config = self.picam2.create_still_configuration(main={"size": resolution}, transform=transformation)
        elif self.capture_mode == CAPTURE_MODES.VIDEO:
            config = self.picam2.create_video_configuration(main={"size": resolution}, encode="main", transform=transformation)
        else:
            config = self.picam2.create_preview_configuration(main={"size": resolution}, transform=transformation)

        self.picam2.configure(config)

        self.picam2.set_controls({
            "AeEnable": self.settings.get("cam_ae_enable", True),                                   # Enable auto exposure
            "AfMode": AF_MODE.get(str(self.settings.get("cam_af_mode")), AfModeEnum.Continuous),    # Auto Focus Mode, AfModeEnum values: Manual, Auto, Continuous
            "AfRange": AF_RANGE.get(str(self.settings.get("cam_af_range")), AfRangeEnum.Normal),    # Auto Focus Range, AfRangeEnum values: Normal, Macro, Full
            "AfSpeed": AF_SPEED.get(str(self.settings.get("cam_af_speed")), AfSpeedEnum.Normal),    # Auto Focus Speed, AfSpeedEnum values: Normal, Fast
            "AwbEnable": self.settings.get("cam_awb_enable", True),                                 # Enable auto white balance
            "AwbMode": AWB_MODE.get(str(self.settings.get("cam_awb_mode")), AwbModeEnum.Auto),      # Auto White Balance Mode, AwbModeEnum values: Auto, Tungsten, Fluorescent, Indoor, Daylight, Cloudy, Custom)
            "Brightness": self.settings.get("cam_brightness", 0.0),                                 # Floating point value from -1.0 to 1.0; 0.0 is default, -1.0 is minimum brightness, 1.0 is maximum brightness
            "Contrast": self.settings.get("cam_contrast", 1.0),                                     # Floating point value from 0.0 to 32.0; 0.0 is no contrast, 1.0 is default, 32.0 is maximum contrast
            "ExposureValue": self.settings.get("cam_exposure_value", 0.0),                          # Floating point value from -8.0 to 8.0; 0.0 is default, positive values brighten the image
            "Saturation": self.settings.get("cam_saturation", 1.0),                                 # Floating point value from 0.0 to 32.0; 0.0 is no saturation, 1.0 is default, 32.0 is maximum saturation
            "Sharpness": self.settings.get("cam_sharpness", 1.0),                                   # Floating point value from 0.0 to 16.0; 1.0 is default, 16.0 is maximum sharpness
        })

        self.picam2.start()

    def reconfigure_camera(self):
        """
        Reconfigures the camera with updated settings.
        This method stops the current camera instance and re-initializes it with the current settings.
        """
        self.picam2.stop()
        self.initialize_camera()

    @property
    def max_resolution(self) -> tuple[int, int]:
        """
        Get the maximum resolution for the current camera model and capture mode.
        
        Returns:
            tuple[int, int]: Maximum resolution as (width, height).
        
        Raises:
            KeyError: If the camera model or capture mode is unsupported.
            TypeError: If the camera model or capture mode is not set.
        """
        try:
            return MAX_RESOLUTIONS[self.camera_model][self.capture_mode] # type: ignore
        except KeyError:
            logger.error(f"Unsupported camera model {self.camera_model} or capture mode {self.capture_mode}. Defaulting to (1920, 1080).")
            return (1920, 1080)
        except TypeError:
            logger.error(f"Camera model or capture mode not set. Defaulting to (1920, 1080).")
            return (1920, 1080)

    def get_resolution(self) -> tuple[int, int]:
        """
        Get the requested resolution from settings, ensuring it does not exceed the maximum supported resolution for the camera_model and capture_mode.

        Returns:
            tuple[int, int]: The resolution to be used for capturing images or videos.

        Raises:
            ValueError: If the requested resolution exceeds the maximum supported resolution.
        """
        requested_resolution = self.settings.get("cam_resolution", self.max_resolution)

        if requested_resolution is None:
            requested_resolution = self.max_resolution

        try:
            if requested_resolution[0] <= self.max_resolution[0] and requested_resolution[1] <= self.max_resolution[1]:
                return requested_resolution
            else:
                raise ValueError(f"Requested resolution {requested_resolution} exceeds maximum for {self.camera_model} in mode: {self.capture_mode}.")
        except ValueError as e:
            logger.error(f"Value Error: {e}. Returning max resolution {self.max_resolution} for {self.camera_model} in mode: {self.capture_mode}")
            return self.max_resolution

    def capture_image(self, output_filepath: Path | None=None):
        """
        Captures a still image and saves it to the specified filepath.

        Args:
            output_filepath (Path): File to save the captured image.
        
        Raises:
            ValueError: If output_filepath is not provided.
        """
        if output_filepath is None:
            try:
                raise(ValueError("Output filepath must be provided to save the captured image."))
            except ValueError as e:
                logger.error(e)
                return
        self.picam2.capture_file(str(output_filepath))

    def start_video(self, output_filepath: Path | None=None):
        """
        Captures a video recording and saves it to the specified filepath.

        Args:
            output_filepath (Path): File to save the recorded video.

        Raises:
            ValueError: If output_filepath is not provided.
        """
        if output_filepath is None:
            try:
                raise(ValueError("Output filepath must be provided to save the recorded video."))
            except ValueError as e:
                logger.error(e)
                return
        encoder = H264Encoder(bitrate=10000000)
        output = FfmpegOutput(str(output_filepath))
        self.picam2.start_recording(
            encoder,
            output,
            name="main"
        )

    def stop_video(self):
        """
        Stops the ongoing video recording.
        """
        self.picam2.stop_recording()