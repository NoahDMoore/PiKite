import asyncio

from pikite.core.pikite_app import PiKiteApp
import pikite.utils.logger as logger_module

# Setup Logger
logger = logger_module.get_logger(__name__)

async def main():
    app = await PiKiteApp.create()

    try:
        await app.run()
    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: Exiting PiKite")
    

if __name__ == "__main__":
    asyncio.run(main())