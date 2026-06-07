from __future__ import annotations 
from typing import TYPE_CHECKING, Callable

from pikite.core.constants import CAPTURE_MODES
from pikite.utils.logger import get_logger
from pikite.utils.timer import Timer

if TYPE_CHECKING:
    from pikite.core.capture_session import CaptureSession
    from pikite.core.menu import Menu
    from pikite.core.modes.pikite_mode import PiKiteMode
    from pikite.core.settings import Settings
    from pikite.hardware.servo_controller import PanServo, TiltServo
    from pikite.remote.remote_server import RemoteServer
    from pikite.system.storage import StorageManager


logger = get_logger(__name__)

class RemoteAPI:
    def __init__(self,
        menu: Menu,
        pan_servo: PanServo,
        remote_server: RemoteServer,
        settings: Settings,
        storage_manager: StorageManager,
        tilt_servo: TiltServo
    ):
        self.menu = menu
        self.pan_servo = pan_servo
        self.remote_server = remote_server
        self.settings = settings
        self.storage_manager = storage_manager
        self.tilt_servo = tilt_servo
        self.timer = Timer()
        self._get_current_mode: Callable[[], PiKiteMode | None] | None = None

    # Mode Endpoint
    def tx_new_mode(self, new_mode: PiKiteMode):
        """Transmit the current mode to remote clients"""
        mode_payload = {
            "type": "mode_update",
            "mode": new_mode
        }

        self.remote_server.send(mode_payload)
        logger.debug("Sent current mode to remote clients")

    def register_mode_provider(self, provider: Callable[[], PiKiteMode | None]):
        if not isinstance(provider, Callable):
            logger.error("Mode provider must be a callback method returning a PiKiteMode enum or None.")
            return
        
        self._get_current_mode = provider

    def tx_current_mode(self):
        if self._get_current_mode is None:
            logger.warning("Could not transmit current mode to remote client. No mode provider registered.")
            return

        mode_payload = {
            "type": "mode_update",
            "mode": self._get_current_mode()
        }

        self.remote_server.send(mode_payload)

    # Settings Endpoints
    def tx_settings(self, **kwargs):
        """Fetch current settings and menu options to send to remote clients."""
        current_settings = self.settings.format_as_dict()
        menu_settings = self.menu.format_settings_and_options_as_dict()
        payload = {
            "type": "settings_update",
            "current_settings": current_settings,
            "menu_settings": menu_settings
        }

        self.remote_server.send(payload)
        logger.debug("Sent current settings and menu options to remote clients")

    def rx_settings_update(self, args):
        self.settings.update_from_dict(args.get("settings_to_update", {}))
        self.tx_settings()  # Send updated settings back to client

    def rx_default_settings_request(self, **kwargs):
        self.settings.load_defaults()
        self.tx_settings()  # Send updated settings back to client


    # Media Endpoints
    def tx_media_dirs(self, **kwargs):
        payload = {
            "type": "media_dirs_update",
            "media_dirs": self.storage_manager.get_capture_session_dirs()
        }
        self.remote_server.send(payload)

    def tx_media_file_paths(self, args):
        mode = CAPTURE_MODES.STILL if args.get("mode") == "STILL" else CAPTURE_MODES.VIDEO
        path = args.get("path")
        file_paths = self.storage_manager.get_capture_session_file_names(mode, path)
        payload = {
            "type": "media_file_paths",
            "file_paths": file_paths
        }
        self.remote_server.send(payload)


    # Servo Endpoints
    def rx_pan_command(self, args):
        angle = int(args.get("angle"))
        self.pan_servo.rotate_to(angle)
        self.timer.wait(0.5)
        self.tx_servo_positions()

    def rx_tilt_command(self, args):
        angle = args.get("angle")
        self.tilt_servo.angle = int(angle)
        self.timer.wait(0.5)
        self.tx_servo_positions()

    def tx_servo_positions(self):
        self.remote_server.send({
            "type": "pan_tilt_update",
            "pan_servo": round(self.pan_servo.encoder.get_smoothed_angle()),
            "tilt_servo": self.tilt_servo.angle
        })


    # Capture Session Endpoints
    def tx_session_info(self, session: CaptureSession):
        """Send capture session info to remote clients."""
        self.remote_server.send(session.get_info_payload())
    
    def tx_session_update(self, session: CaptureSession):
        """Send capture session update to remote clients."""
        self.remote_server.send(session.get_update_payload())

    def tx_session_end(self, session: CaptureSession):
        """Send session end notification to remote clients."""
        self.remote_server.send(session.get_end_payload())