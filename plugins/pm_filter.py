import re
import ast
import math
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION
from database.ia_filterdb import get_filter_results
from database.connections_mdb import active_connection
from utils import get_size, is_subscribed, get_settings, save_group_settings
from Script import script

logger = logging.getLogger(__name__)


def get_quality(file_name: str) -> str:
    for q in ["2160p", "1080p", "720p", "480p", "360p", "4K"]:
        if q.lower() in file_name.lower():
            return q
    return "🔸 N/A"


def get_lang(file_name: str) -> str:
    for l in ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English"]:
        if l.lower() in file_name.lower():
            if "dubbed" in file_name.lower():
                return f"{l} Dubbed"
            return l
    if "multi" in file_name.lower():
        return "Multi Audio"
    return "🔸 N/A"


def format_result_btn_label(file_name: str) -> str:
    """Short label for inline button."""
    quality = get_quality(file_name)
    lang = get_lang(file_name)
    short = file_name[:35].strip()
    return f"🎬 {short} | {quality}"


@Client.on_callback_query(filters.regex(r"^fileid#"))
async def pm_filter_cb(client, query):
    """Handle file delivery when user taps file button."""
    _, file_id, chat_id = query.data.split("#", 2)
    settings = await get_settings(int(chat_id))

    try:
        file_msg = await client.get_messages(int(chat_id), int(file_id))
    except Exception as e:
        logger.exception(e)
        return await query.answer("❌ File not found!", show_alert=True)

    fname = file_msg.document.file_name if file_msg.document else "Unknown"
    fsize = file_msg.document.file_size if file_msg.document else 0
    quality = get_quality(fname)
    lang = get_lang(fname)
    size_str = get_size(fsize)

    caption = (
        f"🎬 **{fname}**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌐 **Language :** `{lang}`\n"
        f"📊 **Quality  :** `{quality}`\n"
        f"📁 **File Size:** `{size_str}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚡ **Sent by Eva Maria Bot**"
    )

    await query.answer("📨 Sending file...")

    try:
        await client.send_document(
            query.from_user.id,
            document=file_msg.document.file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Share", switch_inline_query=fname[:30])]
            ])
        )
        await query.message.reply(
            "✅ **File sent to your PM!**\n👆 Click the link above to open.",
            quote=True
        )
    except Exception as e:
        logger.exception(e)
        await query.message.reply(
            "⚠️ Start the bot in PM first!\n👉 @YourBotUsername",
            quote=True
        )
