import logging
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from database.ia_filterdb import Media, get_search_results
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, LOG_CHANNEL, CLONE_MODE
from utils import (
    get_settings,
    save_group_settings,
    temp,
    is_subscribed,
    get_size,
    get_shortlink
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── Filter Options ────────────────────────────────────────────────────────────

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "Telugu", "English", "Kannada", "Bengali", "Punjabi"]
QUALITIES = ["480p", "720p", "1080p", "4K", "HDRip", "DVDRip", "BluRay"]


def _lang_buttons(selected: list) -> list:
    rows = []
    for i in range(0, len(LANGUAGES), 2):
        row = []
        for lang in LANGUAGES[i:i+2]:
            tick = "✅ " if lang in selected else ""
            row.append(InlineKeyboardButton(f"{tick}{lang}", callback_data=f"lf_{lang}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("✔ Done", callback_data="lf_done"),
        InlineKeyboardButton("🔄 Reset", callback_data="lf_reset")
    ])
    return rows


def _qual_buttons(selected: list) -> list:
    rows = []
    for i in range(0, len(QUALITIES), 3):
        row = []
        for q in QUALITIES[i:i+3]:
            tick = "✅ " if q in selected else ""
            row.append(InlineKeyboardButton(f"{tick}{q}", callback_data=f"qf_{q}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("✔ Done", callback_data="qf_done"),
        InlineKeyboardButton("🔄 Reset", callback_data="qf_reset")
    ])
    return rows


def _passes_filters(file_name: str, languages: list, qualities: list) -> bool:
    """Return True if file passes active language and quality filters."""
    name = file_name.lower()
    lang_ok = (not languages) or any(l.lower() in name for l in languages)
    qual_ok = (not qualities) or any(q.lower() in name for q in qualities)
    return lang_ok and qual_ok


# ── Language Filter Commands ──────────────────────────────────────────────────

@Client.on_message(filters.command("setlang") & filters.group)
async def set_language_filter(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply("⚠️ Only admins can set filters.")
    settings = await get_settings(message.chat.id)
    selected = settings.get("language_filter", [])
    await message.reply(
        "🌐 **Language Filter**\nSelect languages to include. Leave empty to show all languages.",
        reply_markup=InlineKeyboardMarkup(_lang_buttons(selected))
    )


@Client.on_message(filters.command("setquality") & filters.group)
async def set_quality_filter(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply("⚠️ Only admins can set filters.")
    settings = await get_settings(message.chat.id)
    selected = settings.get("quality_filter", [])
    await message.reply(
        "📺 **Quality Filter**\nSelect qualities to include. Leave empty to show all qualities.",
        reply_markup=InlineKeyboardMarkup(_qual_buttons(selected))
    )


# ── Language Filter Callbacks ─────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^lf_"))
async def language_filter_cb(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS:
        return await query.answer("Only admins can change this!", show_alert=True)
    data = query.data[3:]
    settings = await get_settings(query.message.chat.id)
    selected = list(settings.get("language_filter", []))

    if data == "done":
        await save_group_settings(query.message.chat.id, "language_filter", selected)
        label = ', '.join(selected) if selected else 'All Languages'
        return await query.message.edit(f"✅ Language filter saved: **{label}**")
    elif data == "reset":
        selected = []
        await save_group_settings(query.message.chat.id, "language_filter", [])
    elif data in LANGUAGES:
        if data in selected:
            selected.remove(data)
        else:
            selected.append(data)
        await save_group_settings(query.message.chat.id, "language_filter", selected)

    await query.message.edit_reply_markup(InlineKeyboardMarkup(_lang_buttons(selected)))
    await query.answer()


# ── Quality Filter Callbacks ──────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^qf_"))
async def quality_filter_cb(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS:
        return await query.answer("Only admins can change this!", show_alert=True)
    data = query.data[3:]
    settings = await get_settings(query.message.chat.id)
    selected = list(settings.get("quality_filter", []))

    if data == "done":
        await save_group_settings(query.message.chat.id, "quality_filter", selected)
        label = ', '.join(selected) if selected else 'All Qualities'
        return await query.message.edit(f"✅ Quality filter saved: **{label}**")
    elif data == "reset":
        selected = []
        await save_group_settings(query.message.chat.id, "quality_filter", [])
    elif data in QUALITIES:
        if data in selected:
            selected.remove(data)
        else:
            selected.append(data)
        await save_group_settings(query.message.chat.id, "quality_filter", selected)

    await query.message.edit_reply_markup(InlineKeyboardMarkup(_qual_buttons(selected)))
    await query.answer()


# ── Main Auto Filter Handler ──────────────────────────────────────────────────

@Client.on_message(filters.group & filters.text & filters.incoming)
async def auto_filter(client, message):
    # Ignore commands
    if message.text.startswith("/"):
        return

    chat_id = message.chat.id

    # Check if chat is disabled/banned
    if chat_id in temp.BANNED_CHATS:
        return
    if message.from_user and message.from_user.id in temp.BANNED_USERS:
        return

    settings = await get_settings(chat_id)
    if not settings.get('auto_filter', True):
        return

    query = message.text.strip()
    if not query or len(query) < 3:
        return

    # Check subscription if AUTH_CHANNEL is set
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        btn = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{AUTH_CHANNEL}")]]
        await message.reply(
            "**You need to join our channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # Get language & quality filters for this group
    lang_filter = settings.get("language_filter", [])
    qual_filter = settings.get("quality_filter", [])

    # Fetch results from DB (fetch more to allow for filter narrowing)
    fetch_limit = 200 if (lang_filter or qual_filter) else 10
    files, next_offset, total = await get_search_results(query, max_results=fetch_limit)

    if not files:
        btn = [[InlineKeyboardButton("🔍 Search Again", switch_inline_query_current_chat=query)]]
        await message.reply(
            f"**No results found for** `{query}`\n\nMake sure you spelled it correctly.",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # Apply language and quality filters
    if lang_filter or qual_filter:
        files = [f for f in files if _passes_filters(f.file_name or "", lang_filter, qual_filter)]

    if not files:
        active_filters = []
        if lang_filter:
            active_filters.append(f"Language: {', '.join(lang_filter)}")
        if qual_filter:
            active_filters.append(f"Quality: {', '.join(qual_filter)}")
        await message.reply(
            f"**No results match your active filters:**\n"
            f"`{chr(10).join(active_filters)}`\n\n"
            f"Use /setlang or /setquality to change filters."
        )
        return

    # ── Build result buttons ──────────────────────────────────────────────────
    btn = []
    for file in files[:10]:
        # Track request count for trending feature
        await Media.increment_request_count(file.file_id)

        file_name = file.file_name
        file_size = get_size(file.file_size)
        btn.append(
            [InlineKeyboardButton(
                f"🎬 {file_name} [{file_size}]",
                callback_data=f"fileid#{file.file_id}"
            )]
        )

    # Add filter status row if filters are active
    status_parts = []
    if lang_filter:
        status_parts.append(f"🌐 {', '.join(lang_filter)}")
    if qual_filter:
        status_parts.append(f"📺 {', '.join(qual_filter)}")
    if status_parts:
        btn.append([InlineKeyboardButton(
            "Active Filters: " + " | ".join(status_parts),
            callback_data="filter_info"
        )])

    await message.reply(
        f"**Here are the results for** `{query}`\n"
        f"**Total found:** `{len(files)}`",
        reply_markup=InlineKeyboardMarkup(btn)
    )


# ── Filter Info Callback (non-functional info button) ─────────────────────────

@Client.on_callback_query(filters.regex(r"^filter_info$"))
async def filter_info_cb(client: Client, query: CallbackQuery):
    settings = await get_settings(query.message.chat.id)
    lang = settings.get("language_filter", [])
    qual = settings.get("quality_filter", [])
    text = (
        f"**Active Filters for this group:**\n\n"
        f"🌐 Language: `{', '.join(lang) if lang else 'All'}`\n"
        f"📺 Quality: `{', '.join(qual) if qual else 'All'}`\n\n"
        f"Admins can change using /setlang and /setquality"
    )
    await query.answer(text, show_alert=True)
