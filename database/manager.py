"""
============================================================================
TELEGRAM UPTIME BOT - BOT MANAGER
============================================================================
Main bot initialization and management.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import router
from bot.admin_handlers import admin_router
from utils import get_logger
from config import get_settings


logger = get_logger(__name__)
settings = get_settings()


# ============================================================================
# BOT MANAGER CLASS
# ============================================================================

class BotManager:
    """
    Main bot manager class.
    Handles bot initialization, routing, and lifecycle management.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize bot manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._is_running = False

        logger.info("BotManager initialized")

    async def initialize(self) -> bool:
        """
        Initialize bot and dispatcher.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing bot...")

            # Create bot instance
            self.bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Create dispatcher with memory storage
            storage = MemoryStorage()
            self.dp = Dispatcher(storage=storage)

            # Register routers
            self.dp.include_router(router)
            self.dp.include_router(admin_router)

            # Register middleware to inject db_manager
            @self.dp.message.middleware()
            async def db_middleware(handler, event, data):
                data['db_manager'] = self.db_manager
                data['bot'] = self.bot
                return await handler(event, data)

            @self.dp.callback_query.middleware()
            async def db_callback_middleware(handler, event, data):
                data['db_manager'] = self.db_manager
                data['bot'] = self.bot
                return await handler(event, data)

            # Set bot commands
            await self._set_bot_commands()

            logger.info("✓ Bot initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}", exc_info=True)
            return False

    async def _set_bot_commands(self):
        """Set bot commands for menu."""
        from aiogram.types import BotCommand

        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="Show help"),
            BotCommand(command="add", description="Add new link"),
            BotCommand(command="list", description="Show all links"),
            BotCommand(command="stats", description="Show statistics"),
            BotCommand(command="settings", description="Bot settings"),
        ]

        # Add admin commands for admin users
        admin_commands = commands + [
            BotCommand(command="admin", description="Admin panel"),
            BotCommand(command="broadcast", description="Broadcast message"),
            BotCommand(command="users", description="List all users"),
            BotCommand(command="system", description="System status"),
        ]

        try:
            # Set default commands
            await self.bot.set_my_commands(commands)
            
            # Set admin commands for owner
            from aiogram.types import BotCommandScopeChat
            for admin_id in settings.admin_list:
                await self.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )

            logger.info("Bot commands set successfully")

        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")

    async def start_polling(self):
        """Start bot in polling mode."""
        try:
            if not self.bot or not self.dp:
                logger.error("Bot not initialized")
                return

            logger.info("Starting bot polling...")
            self._is_running = True

            # Delete webhook if exists
            await self.bot.delete_webhook(drop_pending_updates=True)

            # Start polling
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types()
            )

        except Exception as e:
            logger.error(f"Error in polling: {e}", exc_info=True)
        finally:
            self._is_running = False

    async def start_webhook(self, webhook_url: str, webhook_path: str, port: int):
        """
        Start bot in webhook mode.

        Args:
            webhook_url: Webhook URL
            webhook_path: Webhook path
            port: Port to listen on
        """
        try:
            if not self.bot or not self.dp:
                logger.error("Bot not initialized")
                return

            logger.info(f"Starting bot webhook on {webhook_url}")
            self._is_running = True

            # Set webhook
            await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )

            # Start webhook
            from aiohttp import web

            app = web.Application()
            
            # Setup webhook handler
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=self.dp,
                bot=self.bot
            )
            webhook_requests_handler.register(app, path=webhook_path)
            setup_application(app, self.dp, bot=self.bot)

            # Run web app
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()

            logger.info(f"✓ Webhook started on port {port}")

            # Keep running
            while self._is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
        finally:
            self._is_running = False

    async def stop(self):
        """Stop the bot gracefully."""
        try:
            logger.info("Stopping bot...")
            self._is_running = False

            if self.bot:
                # Delete webhook
                await self.bot.delete_webhook()
                
                # Close bot session
                await self.bot.session.close()

            if self.dp:
                await self.dp.storage.close()

            logger.info("✓ Bot stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._is_running


# ============================================================================
# END OF BOT MANAGER MODULE
# ============================================================================
