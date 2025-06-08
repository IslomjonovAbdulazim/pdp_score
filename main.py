# main.py
import logging
from config import Config
from database import initialize_database
from bot.bot_setup import setup_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    try:
        # Display configuration
        Config.display_config()

        # Initialize database
        logger.info("Initializing database...")
        initialize_database()

        # Setup and start bot
        logger.info("Starting Telegram bot...")
        application = setup_bot()

        # Start the bot
        logger.info("Bot is running! Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=['message', 'callback_query'])

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    main()