"""
============================================================================
TELEGRAM UPTIME BOT - ADMIN HANDLERS
============================================================================
Admin panel and administrative command handlers.

Author: Professional Development Team
Version: 1.0.0
License: MIT  
============================================================================
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, func

from database import DatabaseManager, UserRepository, LinkRepository, User, MonitoredLink, Statistics
from database.models import UserRole, UserStatus
from utils import get_logger, StringHelper, TimeHelper, PerformanceHelper
from config import get_settings


logger = get_logger(__name__)
settings = get_settings()

# Create admin router
admin_router = Router()


# ============================================================================
# FSM STATES
# ============================================================================

class BroadcastStates(StatesGroup):
    """States for broadcast functionality."""
    waiting_for_message = State()
    confirming = State()


class UserManagementStates(StatesGroup):
    """States for user management."""
    selecting_user = State()
    selecting_action = State()
    waiting_for_input = State()


# ============================================================================
# ADMIN KEYBOARDS
# ============================================================================

class AdminKeyboards:
    """Admin-specific keyboards."""

    @staticmethod
    def admin_panel() -> InlineKeyboardMarkup:
        """Main admin panel keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
                InlineKeyboardButton(text="🔗 Links", callback_data="admin_links")
            ],
            [
                InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="💾 Database", callback_data="admin_database"),
                InlineKeyboardButton(text="🔧 System", callback_data="admin_system")
            ],
            [
                InlineKeyboardButton(text="📝 Logs", callback_data="admin_logs"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_refresh")
            ],
            [
                InlineKeyboardButton(text="« Main Menu", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def user_management(user_id: int) -> InlineKeyboardMarkup:
        """User management keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="✏️ Edit Role", callback_data=f"admin_user_role:{user_id}"),
                InlineKeyboardButton(text="🎁 Set Premium", callback_data=f"admin_user_premium:{user_id}")
            ],
            [
                InlineKeyboardButton(text="📊 User Stats", callback_data=f"admin_user_stats:{user_id}"),
                InlineKeyboardButton(text="🔗 User Links", callback_data=f"admin_user_links:{user_id}")
            ],
            [
                InlineKeyboardButton(text="🚫 Ban", callback_data=f"admin_user_ban:{user_id}"),
                InlineKeyboardButton(text="🗑️ Delete", callback_data=f"admin_user_delete:{user_id}")
            ],
            [
                InlineKeyboardButton(text="« Back", callback_data="admin_users")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def confirm_action(action: str, data: str) -> InlineKeyboardMarkup:
        """Confirmation keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"admin_confirm:{action}:{data}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="admin_cancel")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# ADMIN HELPERS
# ============================================================================

class AdminHelpers:
    """Helper functions for admin operations."""

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in settings.admin_list

    @staticmethod
    async def get_system_stats(db_manager: DatabaseManager) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            async with db_manager.session() as session:
                # User stats
                total_users = await session.scalar(select(func.count(User.id)))
                active_users = await session.scalar(
                    select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
                )
                premium_users = await session.scalar(
                    select(func.count(User.id)).where(User.is_premium == True)
                )

                # Link stats
                total_links = await session.scalar(select(func.count(MonitoredLink.id)))
                active_links = await session.scalar(
                    select(func.count(MonitoredLink.id)).where(MonitoredLink.is_active == True)
                )
                up_links = await session.scalar(
                    select(func.count(MonitoredLink.id)).where(MonitoredLink.is_up == True)
                )

                # Performance stats
                memory_mb = PerformanceHelper.get_memory_usage()
                cpu_percent = PerformanceHelper.get_cpu_usage()

                return {
                    "users": {
                        "total": total_users,
                        "active": active_users,
                        "premium": premium_users
                    },
                    "links": {
                        "total": total_links,
                        "active": active_links,
                        "up": up_links,
                        "down": total_links - up_links
                    },
                    "performance": {
                        "memory_mb": memory_mb,
                        "cpu_percent": cpu_percent
                    }
                }

        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}

    @staticmethod
    def format_system_stats(stats: Dict[str, Any]) -> str:
        """Format system statistics for display."""
        return f"""
🔧 <b>System Statistics</b>

<b>👥 Users:</b>
• Total: {stats['users']['total']}
• Active: {stats['users']['active']}
• Premium: {stats['users']['premium']}

<b>🔗 Links:</b>
• Total: {stats['links']['total']}
• Active: {stats['links']['active']}
• Up: {stats['links']['up']} 🟢
• Down: {stats['links']['down']} 🔴

<b>⚡ Performance:</b>
• Memory: {stats['performance']['memory_mb']:.2f} MB
• CPU: {stats['performance']['cpu_percent']:.1f}%

<b>🕐 Updated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""


# ============================================================================
# ADMIN COMMAND HANDLERS
# ============================================================================

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, db_manager: DatabaseManager):
    """
    Handle /admin command.
    Opens admin panel for authorized users.
    """
    if not AdminHelpers.is_admin(message.from_user.id):
        await message.answer("❌ You don't have permission to access admin panel.")
        return

    try:
        stats = await AdminHelpers.get_system_stats(db_manager)
        stats_text = AdminHelpers.format_system_stats(stats)

        await message.answer(
            f"👑 <b>Admin Panel</b>\n\n{stats_text}",
            parse_mode="HTML",
            reply_markup=AdminKeyboards.admin_panel()
        )

        logger.info(f"Admin {message.from_user.id} accessed admin panel")

    except Exception as e:
        logger.error(f"Error in admin command: {e}", exc_info=True)
        await message.answer("❌ Error loading admin panel.")


@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """
    Handle /broadcast command.
    Initiates broadcast message to all users.
    """
    if not AdminHelpers.is_admin(message.from_user.id):
        await message.answer("❌ Unauthorized.")
        return

    try:
        await state.set_state(BroadcastStates.waiting_for_message)
        await message.answer(
            "📢 <b>Broadcast Message</b>\n\n"
            "Send the message you want to broadcast to all users.\n\n"
            "You can use HTML formatting.\n\n"
            "Send /cancel to abort.",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await message.answer("❌ Error occurred.")


@admin_router.message(Command("users"))
async def cmd_users(message: Message, db_manager: DatabaseManager):
    """
    Handle /users command.
    Shows list of all users.
    """
    if not AdminHelpers.is_admin(message.from_user.id):
        await message.answer("❌ Unauthorized.")
        return

    try:
        user_repo = UserRepository(db_manager)
        users = await user_repo.get_all(User, limit=20)

        if not users:
            await message.answer("No users found.")
            return

        text = "👥 <b>Users (Top 20):</b>\n\n"
        
        for idx, user in enumerate(users, 1):
            status_emoji = "🟢" if user.status == UserStatus.ACTIVE else "🔴"
            premium_badge = "✨" if user.is_premium else ""
            
            text += (
                f"{idx}. {status_emoji} {premium_badge} "
                f"<b>{StringHelper.escape_html(user.full_name)}</b>\n"
                f"   ID: <code>{user.user_id}</code> | "
                f"Links: {user.current_link_count}/{user.max_links}\n\n"
            )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in users command: {e}")
        await message.answer("❌ Error occurred.")


@admin_router.message(Command("system"))
async def cmd_system(message: Message, db_manager: DatabaseManager):
    """
    Handle /system command.
    Shows system information and health.
    """
    if not AdminHelpers.is_admin(message.from_user.id):
        await message.answer("❌ Unauthorized.")
        return

    try:
        # Get database info
        db_info = await db_manager.get_database_info()
        
        # Get system stats
        stats = await AdminHelpers.get_system_stats(db_manager)

        system_text = f"""
🔧 <b>System Information</b>

<b>🗄️ Database:</b>
• Status: {db_info.get('status', 'unknown')}
• Users: {db_info.get('users', 0)}
• Links: {db_info.get('links', 0)}
• Logs: {db_info.get('logs', 0)}

<b>⚡ Performance:</b>
• Memory: {stats['performance']['memory_mb']:.2f} MB
• CPU: {stats['performance']['cpu_percent']:.1f}%

<b>⚙️ Configuration:</b>
• Bot Version: {settings.BOT_VERSION}
• Environment: {'Production' if settings.is_production else 'Development'}
• Debug: {'Enabled' if settings.DEBUG else 'Disabled'}

<b>🕐 System Time:</b>
{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

        await message.answer(system_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in system command: {e}")
        await message.answer("❌ Error occurred.")


# ============================================================================
# BROADCAST FSM HANDLERS
# ============================================================================

@admin_router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Process broadcast message input."""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Broadcast cancelled.")
        return

    try:
        # Store message
        await state.update_data(broadcast_message=message.text)
        await state.set_state(BroadcastStates.confirming)

        # Get user count
        user_repo = UserRepository(db_manager)
        user_count = await user_repo.count(User)

        await message.answer(
            f"📢 <b>Confirm Broadcast</b>\n\n"
            f"<b>Message Preview:</b>\n{message.text}\n\n"
            f"<b>Recipients:</b> {user_count} users\n\n"
            f"Send 'YES' to confirm or /cancel to abort.",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error processing broadcast message: {e}")
        await message.answer("❌ Error occurred.")
        await state.clear()


@admin_router.message(BroadcastStates.confirming)
async def confirm_broadcast(message: Message, state: FSMContext, db_manager: DatabaseManager, bot):
    """Confirm and send broadcast."""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Broadcast cancelled.")
        return

    if message.text.upper() != "YES":
        await message.answer("❌ Please send 'YES' to confirm or /cancel to abort.")
        return

    try:
        data = await state.get_data()
        broadcast_message = data['broadcast_message']

        # Get all active users
        user_repo = UserRepository(db_manager)
        users = await user_repo.get_all_active()

        # Send broadcast
        status_msg = await message.answer("📤 Broadcasting message...")
        
        success_count = 0
        fail_count = 0

        for user in users:
            try:
                await bot.send_message(user.user_id, broadcast_message, parse_mode="HTML")
                success_count += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception as e:
                fail_count += 1
                logger.warning(f"Failed to send broadcast to {user.user_id}: {e}")

        await status_msg.edit_text(
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"• Successful: {success_count}\n"
            f"• Failed: {fail_count}\n"
            f"• Total: {success_count + fail_count}",
            parse_mode="HTML"
        )

        await state.clear()
        logger.info(f"Broadcast sent: {success_count} success, {fail_count} failed")

    except Exception as e:
        logger.error(f"Error in broadcast: {e}", exc_info=True)
        await message.answer("❌ Broadcast failed.")
        await state.clear()


# ============================================================================
# ADMIN CALLBACK HANDLERS
# ============================================================================

@admin_router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, db_manager: DatabaseManager):
    """Show admin panel."""
    if not AdminHelpers.is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return

    try:
        stats = await AdminHelpers.get_system_stats(db_manager)
        stats_text = AdminHelpers.format_system_stats(stats)

        await callback.message.edit_text(
            f"👑 <b>Admin Panel</b>\n\n{stats_text}",
            parse_mode="HTML",
            reply_markup=AdminKeyboards.admin_panel()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin panel callback: {e}")
        await callback.answer("❌ Error occurred")


@admin_router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, db_manager: DatabaseManager):
    """Show detailed statistics."""
    if not AdminHelpers.is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return

    try:
        stats = await AdminHelpers.get_system_stats(db_manager)
        
        # Calculate additional metrics
        uptime_ratio = 0
        if stats['links']['total'] > 0:
            uptime_ratio = (stats['links']['up'] / stats['links']['total']) * 100

        detailed_stats = f"""
📊 <b>Detailed Statistics</b>

<b>👥 Users:</b>
• Total: {stats['users']['total']}
• Active: {stats['users']['active']}
• Premium: {stats['users']['premium']}
• Ratio: {(stats['users']['active']/stats['users']['total']*100) if stats['users']['total'] > 0 else 0:.1f}%

<b>🔗 Links:</b>
• Total: {stats['links']['total']}
• Active: {stats['links']['active']}
• Up: {stats['links']['up']} ({uptime_ratio:.1f}%)
• Down: {stats['links']['down']}

<b>⚡ System:</b>
• Memory: {stats['performance']['memory_mb']:.2f} MB
• CPU: {stats['performance']['cpu_percent']:.1f}%
• Version: {settings.BOT_VERSION}

<b>🕐 Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

        await callback.message.edit_text(
            detailed_stats,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton(text="« Back", callback_data="admin_panel")]
            ])
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin stats: {e}")
        await callback.answer("❌ Error occurred")


@admin_router.callback_query(F.data == "admin_database")
async def cb_admin_database(callback: CallbackQuery, db_manager: DatabaseManager):
    """Show database information."""
    if not AdminHelpers.is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return

    try:
        db_info = await db_manager.get_database_info()

        db_text = f"""
💾 <b>Database Information</b>

<b>Status:</b> {db_info.get('status', 'unknown')}

<b>Tables:</b>
• Users: {db_info.get('users', 0)}
• Links: {db_info.get('links', 0)}
• Logs: {db_info.get('logs', 0)}
• Alerts: {db_info.get('alerts', 0)}

<b>Connection:</b>
• Pool Size: {settings.DB_POOL_SIZE}
• Type: {settings.DB_TYPE}

<b>Checked:</b> {db_info.get('checked_at', 'N/A')}
"""

        await callback.message.edit_text(
            db_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Check", callback_data="admin_database")],
                [InlineKeyboardButton(text="« Back", callback_data="admin_panel")]
            ])
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in database info: {e}")
        await callback.answer("❌ Error occurred")


@admin_router.callback_query(F.data == "admin_refresh")
async def cb_admin_refresh(callback: CallbackQuery, db_manager: DatabaseManager):
    """Refresh admin panel."""
    await cb_admin_panel(callback, db_manager)


@admin_router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(callback: CallbackQuery):
    """Cancel admin operation."""
    await callback.message.edit_text("❌ Operation cancelled.")
    await callback.answer()


# ============================================================================
# END OF ADMIN HANDLERS MODULE
# ============================================================================
