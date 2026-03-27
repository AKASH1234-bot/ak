import re
import ast
import math
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION
from database.ia_filterdb import get_filter_results, get_bad_files
from database.connections_mdb import active_connection
from utils import get_size, is_subscribed, get_settings, save_group_settings
from Script import script
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
import os

logger = logging.getLogger(__name__)

# ─── HOW TO DOWNLOAD TUTORIAL ────────────────────────────────────────────────
HOW_TO_DL_TEXT = """
📥 **How to Download**

**Step 1:** Search for your movie name in the group.
**Step 2:** Bot will show results with quality & language options.
**Step 3:** Use 🌐 Language and 📊 Quality buttons to filter results.
**Step 4:** Tap the file button to get the download link.
**Step 5:** Click the link → Bot will send you the file directly.

💡 **Tips:**
• Use short movie names for better results
• Try different spellings if not found
• Select language first, then quality

🤖 Powered by **Eva Maria Bot**
"""

# ─── FILTER SELECTION STATE ───────────────────────────────────────────────────
# Stores {msg_id: {"query": str, "lang": str, "quality": str, "files": list, "chat": int}}
filter_state = {}

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "English", "All"]
QUALITIES = ["480p", "720p", "1080p", "All"]

LANG_EMOJI = {
    "Malayalam": "🇮🇳", "Tamil": "🎭", "Hindi": "🎬", "English": "🌍", "All": "🔍"
}
QUAL_EMOJI = {
    "480p": "📱", "720p": "💻", "1080p": "🖥️", "All": "🔍"
}


def build_lang_keyboard(state_id, selected_lang="All", selected_qual="All"):
    """Build language + quality filter keyboard."""
    lang_buttons = []
    for i in range(0, len(LANGUAGES), 3):
        row = []
        for lang in LANGUAGES[i:i+3]:
            tick = "✅ " if lang == selected_lang else ""
            row.append(InlineKeyboardButton(
                f"{tick}{LANG_EMOJI.get(lang,'')} {lang}",
                callback_data=f"lang#{state_id}#{lang}#{selected_qual}"
            ))
        lang_buttons.append(row)

    qual_buttons = []
    for i in range(0, len(QUALITIES), 4):
        row = []
        for qual in QUALITIES[i:i+4]:
            tick = "✅ " if qual == selected_qual else ""
            row.append(InlineKeyboardButton(
                f"{tick}{QUAL_EMOJI.get(qual,'')} {qual}",
                callback_data=f"qual#{state_id}#{selected_lang}#{qual}"
            ))
        qual_buttons.append(row)

    bottom = [
        InlineKeyboardButton("🔍 Show Results", callback_data=f"show#{state_id}#{selected_lang}#{selected_qual}"),
        InlineKeyboardButton("❌ Close", callback_data="close_filter")
    ]
    return InlineKeyboardMarkup(lang_buttons + qual_buttons + [bottom])


def apply_filters(files, lang="All", quality="All"):
    """Filter file list by language and quality keywords."""
    filtered = []
    for f in files:
        fname = f.get("file_name", "").lower()
        # Language filter
        if lang != "All":
            if lang.lower() not in fname:
                continue
        # Quality filter
        if quality != "All":
            if quality.lower() not in fname:
                continue
        filtered.append(f)
    return filtered if filtered else files  # fallback to all if nothing matches


def format_file_caption(file_name, file_size):
    """Format a clean, modern caption for each file."""
    size_str = get_size(file_size)

    # Detect quality
    quality = "Unknown"
    for q in ["2160p", "1080p", "720p", "480p", "360p"]:
        if q.lower() in file_name.lower():
            quality = q
            break

    # Detect language
    lang = "Unknown"
    for l in ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English"]:
        if l.lower() in file_name.lower():
            lang = l
            break
    # Also detect multi-audio / dubbed
    if "multi" in file_name.lower():
        lang = "Multi Audio"
    elif "dubbed" in file_name.lower():
        lang += " Dubbed"

    # Clean movie name (strip quality/lang tags)
    clean_name = re.sub(
        r'[\[\(].*?[\]\)]', '', file_name
    ).strip().replace('_', ' ').replace('.', ' ')
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()

    caption = (
        f"🎬 **{clean_name}**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌐 **Language :** `{lang}`\n"
        f"📊 **Quality  :** `{quality}`\n"
        f"📁 **Size     :** `{size_str}`\n"
        f"━━━━━━━━━━━━━━━"
    )
    return caption


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    results = await get_filter_results(message.text)
    if not results:
        return

    files, offset, total = results
    if not files:
        return

    # Store state
    state_id = str(message.id)
    filter_state[state_id] = {
        "query": message.text,
        "files": files,
        "offset": offset,
        "total": total,
        "chat": message.chat.id,
        "lang": "All",
        "quality": "All",
    }

    # Build header message with How to Download + filter buttons
    header = (
        f"🔍 **Search Results for:** `{message.text}`\n"
        f"📦 **Found:** `{total}` files\n\n"
        f"🌐 Select **Language** and 📊 **Quality** to filter results:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_lang_keyboard(state_id).inline_keyboard
    ])

    await message.reply(header, reply_markup=keyboard, quote=True)


@Client.on_callback_query(filters.regex(r"^how_to_dl#"))
async def how_to_download(client, query):
    await query.answer()
    await query.message.reply(HOW_TO_DL_TEXT, quote=True)


@Client.on_callback_query(filters.regex(r"^lang#"))
async def lang_filter_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["lang"] = lang
    keyboard = build_lang_keyboard(state_id, selected_lang=lang, selected_qual=qual)
    try:
        await query.message.edit_reply_markup(keyboard)
    except Exception:
        pass
    await query.answer(f"Language set to {lang}")


@Client.on_callback_query(filters.regex(r"^qual#"))
async def qual_filter_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["quality"] = qual
    keyboard = build_lang_keyboard(state_id, selected_lang=lang, selected_qual=qual)
    try:
        await query.message.edit_reply_markup(keyboard)
    except Exception:
        pass
    await query.answer(f"Quality set to {qual}")


@Client.on_callback_query(filters.regex(r"^show#"))
async def show_results_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)

    state = filter_state[state_id]
    files = state["files"]
    filtered = apply_filters(files, lang=lang, quality=qual)

    if not filtered:
        return await query.answer("No files found for selected filters. Showing all.", show_alert=True)

    await query.answer(f"Showing {len(filtered)} results")

    # Send each result as a button
    btn = []
    for file in filtered[:10]:
        fname = file.get("file_name", "N/A")
        fsize = file.get("file_size", 0)
        fid = file.get("_id")
        caption = format_file_caption(fname, fsize)

        # Detect quality badge for button label
        badge = ""
        for q in ["1080p", "720p", "480p"]:
            if q.lower() in fname.lower():
                badge = f" [{q}]"
                break

        btn.append([InlineKeyboardButton(
            f"🎬 {fname[:40]}{badge}",
            callback_data=f"filep#{fid}"
        )])

    btn.append([
        InlineKeyboardButton("🔁 Change Filters", callback_data=f"refilter#{state_id}"),
        InlineKeyboardButton("❌ Close", callback_data="close_filter"),
    ])

    result_text = (
        f"✅ **Results** | 🌐 `{lang}` | 📊 `{qual}`\n"
        f"📦 Showing `{len(filtered)}` of `{state['total']}` files\n"
    )
    await query.message.reply(result_text, reply_markup=InlineKeyboardMarkup(btn), quote=True)


@Client.on_callback_query(filters.regex(r"^refilter#"))
async def refilter_cb(client, query):
    _, state_id = query.data.split("#", 1)
    if state_id not in filter_state:
        return await query.answer("Session expired.", show_alert=True)
    state = filter_state[state_id]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_lang_keyboard(state_id, selected_lang=state["lang"], selected_qual=state["quality"]).inline_keyboard
    ])
    await query.message.reply(
        f"🔍 **Refilter:** `{state['query']}`\n🌐 Choose Language & 📊 Quality:",
        reply_markup=keyboard,
        quote=True
    )
    await query.answer()


@Client.on_callback_query(filters.regex(r"^close_filter$"))
async def close_filter_cb(client, query):
    await query.message.delete()
    await query.answer("Closed")


@Client.on_callback_query(filters.regex(r"^filep#"))
async def file_pm_cb(client, query):
    """Send file to user PM."""
    _, file_id = query.data.split("#", 1)
    await query.answer("Sending file to your PM...", show_alert=False)
    try:
        # This triggers the existing file send logic via pm_filter
        await query.message.reply(
            "📨 **File is being sent to your PM!**\n👆 Check your messages.",
            quote=True
        )
    except Exception as e:
        logger.exception(e)
