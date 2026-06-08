from pikite.hardware.camera.camera_controller import CameraController
from pikite.remote.remote_server import RemoteServer
from pikite.utils.logger import get_logger
from pikite.utils.timer import Timer

import cv2

import asyncio

# Setup Logger
logger = get_logger(__name__)

class PreviewStream:
    def __init__(self, camera: CameraController, server: RemoteServer):
        self.camera = camera
        self.server = server

        self.timer = Timer(name=f"{__name__}.{__class__.__name__}")

        self._active = True

        self.preview_task = None
        self.streaming = False
        self.latest_frame = asyncio.Queue(maxsize=1)

    def start(self):
        """
        Start preview frame generator for streaming preview of camera output.
        """
        if self.streaming:
            logger.warning("Cannot start preview stream because it is already streaming.")
            return

        self.streaming = True
        self.timer.start()
        logger.debug("Starting preview task.")
        self.preview_task = asyncio.create_task(self._preview_stream())

    async def stop(self):
        """
        Stop preview frame generator to end streaming preview of camera output.
        """
        if not self.streaming:
            logger.warning("Cannot stop preview stream because it is not currently streaming.")
            return

        self.streaming = False

        if self.preview_task is not None and not self.preview_task.done():
            logger.debug("Canceling preview task.")
            self.preview_task.cancel()
            try:
                await self.preview_task
            except asyncio.CancelledError:
                self.preview_task = None

        self.timer.stop()
        self._clear_frame_queue()

    async def close(self):
        logger.info("Closing camera preview stream.")
        await self.stop()
        self._active = False
        self.latest_frame.put_nowait("CLOSE") # Ensure stream loop breaks await by adding to latest_frame queue

    def _clear_frame_queue(self):
        while not self.latest_frame.empty():
            try:
                self.latest_frame.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def _preview_stream(self):
        """
        Stores the latest frame from the preview stream.

        Raises:
            ValueError: If the preview is not currently streaming.
        """
        if not self.streaming:
            try:
                raise(ValueError(f"The preview stream is not running. Call start_preview() to initiate preview stream."))
            except ValueError as e:
                logger.warning(e)
                return

        FRAME_RATE = 1 / 10  # 10 FPS

        try:
            logger.info("Camera preview stream started.")

            while self.streaming:
                if not self.timer.interval_elapsed(FRAME_RATE):
                    await asyncio.sleep(0.01)
                    continue

                frame = self.camera.picam2.capture_array("lores")
                frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                )

                image = encoded.tobytes()

                await self.latest_frame.put(image)

                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.debug("Preview stream cancelled")

        logger.info("Camera preview stream stopped")

    async def stream(self):
        logger.info("Camera preview stream ready.")
        try:
            while self._active:
                if not self.streaming:
                    await asyncio.sleep(0)

                    if not self._active:
                        break
                    else:
                        continue

                frame = await self.latest_frame.get()

                if frame == "CLOSE":
                    break

                self.server.send(frame)
        finally:
            logger.info("Camera preview stream has been closed.")