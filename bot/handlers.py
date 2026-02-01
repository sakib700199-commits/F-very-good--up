"""
============================================================================
TELEGRAM UPTIME BOT - BOT HANDLERS
============================================================================
Comprehensive bot command handlers and message processors.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import DatabaseManager, UserRepository, LinkRepository, MonitoredLink, User
from database.models import UserRole, LinkStatus, MonitorType, HTTPMethod
from utils import get_logger, TelegramHelper, StringHelper, TimeHelper
from utils.validators import URLValidator, LinkValidator, DataValidator
from config import get_settings


logger = get_logger(__name__)
settings = get_settings()

# Create router for handlers
router = Router()


# ============================================================================
# FSM STATES
# ============================================================================

class AddLinkStates(StatesGroup):
    """States for adding a new link."""
    waiting_for_url = State()
    waiting_for_name = State()
    waiting_for_interval = State()


class BroadcastStates(StatesGroup):
    """States for broadcasting messages."""
    waiting_for_message = State()
    confirming = State()


# ============================================================================
# KEYBOARDS
# ============================================================================

class Keyboards:
    """Inline keyboard builders."""

    @staticmethod
    def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Build main menu keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="📊 My Links", callback_data="my_links"),
                InlineKeyboardButton(text="➕ Add Link", callback_data="add_link")
            ],
            [
                InlineKeyboardButton(text="📈 Statistics", callback_data="statistics"),
                InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton(text="❓ Help", callback_data="help")
            ]
        ]

        if is_admin:
            buttons.append([
                InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel")
            ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_panel() -> InlineKeyboardMarkup:
        """Build admin panel keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
                InlineKeyboardButton(text="🔗 All Links", callback_data="admin_links")
            ],
            [
                InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="🔧 System", callback_data="admin_system"),
                InlineKeyboardButton(text="📝 Logs", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton(text="« Back", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def link_actions(link_id: int, is_active: bool) -> InlineKeyboardMarkup:
        """Build link actions keyboard."""
        pause_text = "▶️ Resume" if not is_active else "⏸️ Pause"
        buttons = [
            [
                InlineKeyboardButton(text="📊 Details", callback_data=f"link_details:{link_id}"),
                InlineKeyboardButton(text=pause_text, callback_data=f"link_toggle:{link_id}")
            ],
            [
                InlineKeyboardButton(text="🗑️ Delete", callback_data=f"link_delete:{link_id}"),
                InlineKeyboardButton(text="« Back", callback_data="my_links")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def cancel() -> InlineKeyboardMarkup:
        """Build cancel keyboard."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

class BotHelpers:
    """Helper functions for bot handlers."""

    @staticmethod
    async def get_or_create_user(db_manager: DatabaseManager, message: Message) -> Optional[User]:
        """Get or create user from message."""
        try:
            user_repo = UserRepository(db_manager)
            
            user = await user_repo.get_or_create(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code
            )

            await user_repo.update_activity(message.from_user.id)
            return user

        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            return None

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in settings.admin_list

    @staticmethod
    def format_link_info(link: MonitoredLink) -> str:
        """Format link information for display."""
        status_emoji = TelegramHelper.format_uptime_status(link.is_up)
        
        info = f"""
🔗 <b>{StringHelper.escape_html(link.display_name)}</b>

<b>URL:</b> {StringHelper.escape_html(link.url)}
<b>Status:</b> {status_emoji}
<b>Uptime:</b> {link.uptime_percentage:.2f}%

<b>Statistics:</b>
• Total Checks: {link.total_checks}
• Successful: {link.successful_checks}
• Failed: {link.failed_checks}

<b>Performance:</b>
• Avg Response: {link.avg_response_time:.3f}s if link.avg_response_time else 'N/A'}
• Last Check: {TimeHelper.get_time_ago(link.last_checked) if link.last_checked else 'Never'}

<b>Settings:</b>
• Interval: {TimeHelper.seconds_to_human_readable(link.ping_interval)}
• Type: {link.monitor_type.value.upper()}
"""
        return info.strip()

    @staticmethod
    def format_user_stats(user: User, links: List[MonitoredLink]) -> str:
        """Format user statistics."""
        active_links = sum(1 for link in links if link.is_active)
        up_links = sum(1 for link in links if link.is_up)
        down_links = sum(1 for link in links if not link.is_up)

        avg_uptime = sum(link.uptime_percentage for link in links) / len(links) if links else 0

        stats = f"""
📊 <b>Your Statistics</b>

<b>Links:</b>
• Total: {len(links)}/{user.max_links}
• Active: {active_links}
• Up: {up_links} 🟢
• Down: {down_links} 🔴

<b>Performance:</b>
• Average Uptime: {avg_uptime:.2f}%

<b>Account:</b>
• Role: {user.role.value.title()}
• Member Since: {user.created_at.strftime('%Y-%m-%d')}
"""
        return stats.strip()


# ============================================================================
# COMMAND HANDLERS - Continue in next file due to length
# ============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message, db_manager: DatabaseManager):
    """Handle /start command."""
    try:
        user = await BotHelpers.get_or_create_user(db_manager, message)
        if not user:
            await message.answer("❌ Error initializing user.")
            return

        is_admin = BotHelpers.is_admin(message.from_user.id)

        welcome = f"""
👋 <b>Welcome to {settings.BOT_NAME}!</b>

Monitor your websites 24/7 with real-time uptime tracking!

<b>Your Account:</b>
• Role: {user.role.value.title()}
• Max Links: {user.max_links}

Use buttons below to get started! 🚀
"""

        await message.answer(welcome, reply_markup=Keyboards.main_menu(is_admin), parse_mode="HTML")
        logger.info(f"User {message.from_user.id} started bot")

    except Exception as e:
        logger.error(f"Error in start: {e}", exc_info=True)
        await message.answer("❌ Error occurred.")


@router.message(Command("add"))
async def cmd_add(message: Message, db_manager: DatabaseManager, state: FSMContext):
    """Handle /add command."""
    try:
        user = await BotHelpers.get_or_create_user(db_manager, message)
        if not user or not user.can_add_link:
            await message.answer(f"❌ Link limit reached ({user.max_links}).")
            return

        await state.set_state(AddLinkStates.waiting_for_url)
        await message.answer("🔗 Send URL to monitor:", reply_markup=Keyboards.cancel())

    except Exception as e:
        logger.error(f"Error in add: {e}", exc_info=True)
        await message.answer("❌ Error occurred.")


@router.message(Command("list"))
async def cmd_list(message: Message, db_manager: DatabaseManager):
    """Handle /list command."""
    try:
        user = await BotHelpers.get_or_create_user(db_manager, message)
        link_repo = LinkRepository(db_manager)
        links = await link_repo.get_user_links(user.user_id)

        if not links:
            await message.answer("📭 No links. Use /add to add one!")
            return

        text = "🔗 <b>Your Links:</b>\n\n"
        for idx, link in enumerate(links, 1):
            status = TelegramHelper.format_uptime_status(link.is_up)
            text += f"{idx}. {link.display_name}\n   {status} | {link.uptime_percentage:.1f}%\n\n"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in list: {e}", exc_info=True)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_manager: DatabaseManager):
    """Handle /stats command."""
    try:
        user = await BotHelpers.get_or_create_user(db_manager, message)
        link_repo = LinkRepository(db_manager)
        links = await link_repo.get_user_links(user.user_id)
        
        stats_text = BotHelpers.format_user_stats(user, links)
        await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in stats: {e}", exc_info=True)


# FSM Handlers
@router.message(AddLinkStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    """Process URL input."""
    url = URLValidator.normalize_url(message.text.strip())
    if not url:
        await message.answer("❌ Invalid URL. Try again:")
        return

    await state.update_data(url=url)
    await state.set_state(AddLinkStates.waiting_for_name)
    await message.answer(f"✅ URL: {url}\n\nProvide name (or /skip):")


@router.message(AddLinkStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Process name input."""
    name = None if message.text == "/skip" else StringHelper.sanitize_string(message.text, 500)
    
    user = await BotHelpers.get_or_create_user(db_manager, message)
    await state.update_data(name=name)
    await state.set_state(AddLinkStates.waiting_for_interval)
    
    await message.answer(
        f"⏱️ Interval (min {user.min_ping_interval}s)?\nSend seconds or /skip for default ({settings.DEFAULT_PING_INTERVAL}s):"
    )


@router.message(AddLinkStates.waiting_for_interval)
async def process_interval(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Process interval and create link."""
    try:
        user = await BotHelpers.get_or_create_user(db_manager, message)
        
        interval = settings.DEFAULT_PING_INTERVAL
        if message.text != "/skip":
            try:
                interval = int(message.text)
                if not DataValidator.is_valid_interval(interval, user.min_ping_interval):
                    await message.answer(f"❌ Invalid. Min: {user.min_ping_interval}s")
                    return
            except ValueError:
                await message.answer("❌ Invalid number.")
                return

        data = await state.get_data()
        link_repo = LinkRepository(db_manager)
        
        link = MonitoredLink(
            user_id=user.id,
            url=data['url'],
            name=data.get('name'),
            ping_interval=interval,
            monitor_type=MonitorType.HTTPS if data['url'].startswith('https') else MonitorType.HTTP
        )
        
        link = await link_repo.create(link)
        user.increment_link_count()
        
        user_repo = UserRepository(db_manager)
        await user_repo.update(user)
        await state.clear()
        
        await message.answer(
            f"✅ Link added!\n\n🔗 {link.display_name}\nID: {link.id}",
            parse_mode="HTML",
            reply_markup=Keyboards.link_actions(link.id, link.is_active)
        )
        
        logger.info(f"User {user.user_id} added link {link.id}")

    except Exception as e:
        logger.error(f"Error creating link: {e}", exc_info=True)
        await message.answer("❌ Error occurred.")
        await state.clear()


# Callback handlers
@router.callback_query(F.data == "my_links")
async def cb_my_links(callback: CallbackQuery, db_manager: DatabaseManager):
    """Show user's links."""
    try:
        user_repo = UserRepository(db_manager)
        user = await user_repo.get_by_user_id(callback.from_user.id)
        link_repo = LinkRepository(db_manager)
        links = await link_repo.get_user_links(user.user_id)

        if not links:
            await callback.message.edit_text("📭 No links yet!")
            return

        text = "🔗 <b>Your Links:</b>\n\n"
        buttons = []
        
        for idx, link in enumerate(links[:10], 1):
            status = TelegramHelper.format_uptime_status(link.is_up)
            text += f"{idx}. {link.display_name}\n   {status}\n\n"
            buttons.append([InlineKeyboardButton(text=f"{idx}. {link.display_name[:30]}", callback_data=f"link:{link.id}")])

        buttons.append([InlineKeyboardButton(text="« Back", callback_data="back_to_main")])
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in my_links: {e}", exc_info=True)
        await callback.answer("❌ Error")


@router.callback_query(F.data == "back_to_main")
async def cb_back(callback: CallbackQuery):
    """Back to main menu."""
    is_admin = BotHelpers.is_admin(callback.from_user.id)
    await callback.message.edit_text("🏠 Main Menu", reply_markup=Keyboards.main_menu(is_admin))
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel operation."""
    await state.clear()
    await callback.message.edit_text("❌ Cancelled.")
    await callback.answer()


# ============================================================================
# END OF HANDLERS MODULE
# ============================================================================
